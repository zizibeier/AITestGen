# my_auto_test 工程 Rework 说明

> 本文档只做阅读与梳理，**不修改任何源代码**。
> 阅读范围：`/Users/wangziyun/ai-test/my_auto_test`，排除 `venv/`、`.idea/`、`__pycache__/`、`files/` 下的二进制模型文件。
> 生成时间：2026-10-27

---

## 1. 工程概览

| 项 | 内容 |
| --- | --- |
| 测试对象 | JLC 3D Viewer 前端（`https://3d-viewer.jlc.com/`）+ Forface 3D 解析/报价 API（`https://api.forface3d.com`） |
| 测试框架 | pytest 8.4.1 + allure-pytest 2.15.0 |
| HTTP 客户端 | requests 2.32.3（Session + Retry） |
| UI 自动化 | Playwright sync API 1.58.0（另有遗留的 async 写法） |
| 数据 | PyYAML 6.0.2 + 自研占位符引擎 `DataHandle` |
| 断言/报告 | 自研 `BaseAssertion` 家族 + Allure |
| 入口 | `run_tests.py`、`run_tests_with_allure.py`、`run_case.py`，以及各测试文件内的 `__main__` |
| 产物 | `allure-results/` → `allure-report/`；失败截图在 `ui/screenshots/`；日志在 `common/logs/` |
| 仓库 | 有 `.git`（master 分支），提交信息较简略 |

### 1.1 三条测试线

| 线 | 位置 | 现状 |
| --- | --- | --- |
| API | `api/tests/test_analysis.py` | 主链路，结构完整；依赖线上 token、webhook 服务 |
| UI（Playwright sync） | `ui/tests/test_view_operations.py` + `ui/tests/ui_base_test.py` + `ui/context/ui_context.py` | 与基类匹配，设计上可运行（需浏览器与模型文件） |
| UI（模板/历史） | `ui/tests/test_measure.py`、`test_canvs.py`、`test_design.py`、`test_workflow.py`、`test_performance.py`、`test_coverage.py` 以及根目录 `test_case.py` | 引用了未定义的基类 / fixture / 方法，当前无法直接收集执行 |

**一句话总结**：这是一个分层比较清晰、封装度较高的 pytest + Allure 工程，但同时保留了多轮迭代/复制粘贴的痕迹。API 线以 `APIContext` + `Endpoints` 为核心，UI 线以 `UIContext` + `BasePage` + `Methods` 为核心，两条线共用 `BaseTest`、`BaseAssertion`、`AllureHelper` 和一套数据/配置工具。

---

## 2. 目录分层

### 2.1 目录树（关键文件）

```text
my_auto_test/
├── pytest.ini                      # 全局 pytest 配置（标记、addopts、testpaths）
├── requirements.txt                # 依赖清单（UTF-16 编码）
├── run_tests.py                    # 入口：pytest + allure generate + 可选邮件
├── run_tests_with_allure.py        # 入口：跑 UI 视图用例 + 生成报告 + 起 HTTP 服务 + 邮件
├── run_case.py                     # 入口：历史脚本，指向不存在的 test_cases.py
├── test_case.py                    # 历史 async UI 用例，指向不存在的 test_methods.py
│
├── api/                            # ---------- API 测试线 ----------
│   ├── core/                       # 底层能力
│   │   ├── api_context.py          # HTTP 会话、请求发送、历史、Allure 附件
│   │   ├── auth_manager.py         # Token 获取/缓存/刷新
│   │   ├── api_base_test.py        # API 测试基类（继承 common.BaseTest）
│   │   ├── base_api.py             # 名不副实：实际是一份 WebhookListener 副本
│   │   └── base_methods.py         # 空文件
│   ├── endpoints/                  # 业务接口层
│   │   └── analysis_endpoints.py   # 上传文件/链接、查状态、查结果
│   ├── assertions/
│   │   └── api_assertion.py        # HTTP/JSON 断言
│   ├── data/                       # API 测试数据与接口路径配置
│   │   ├── analysis_test_data.yaml # 数据驱动主数据源
│   │   ├── analysis_test_data.py   # YAML → dataclass 的加载器
│   │   ├── analysis_test_data.json # 另一份数据（当前未被引用）
│   │   ├── api_config.yaml         # 接口路径配置
│   │   └── enevts.yaml             # Webhook 事件 ID 字典（当前未被引用）
│   └── tests/
│       ├── conftest.py             # 命令行参数、session fixture、失败钩子、marker
│       └── test_analysis.py        # 参数化上传测试 + webhook 回调测试
│
├── ui/                             # ---------- UI 测试线 ----------
│   ├── context/
│   │   └── ui_context.py           # 页面导航、登录、上传模型、等待加载、iframe
│   ├── pages/
│   │   └── base_page.py            # 定位器加载、元素原子操作、高亮、调试
│   ├── methods/                    # 业务动作层（每个文件一个能力域）
│   │   ├── base_methods.py         # iframe / canvas / 鼠标 / 按钮查找
│   │   ├── view_methods.py         # 旋转、缩放、平移、重置
│   │   ├── measure_methods.py      # 激活测量、测距、清理
│   │   ├── toolbar_methods.py      # 点击/判断工具按钮
│   │   ├── iframe_methods.py       # iframe 内选择/批注/结构树/剖切等
│   │   ├── annotation_methods.py   # 批注操作
│   │   ├── canvas_methods.py       # Canvas 操作
│   │   └── model_info_methods.py   # 模型信息
│   ├── assertions/
│   │   └── ui_assertion.py         # 元素/页面/Canvas 断言
│   ├── locators/                   # 选择器 YAML
│   │   ├── main_page_locators.yaml
│   │   ├── iframe_locators.yaml
│   │   ├── locators.yaml
│   │   └── viewer_locators.yaml    # 空文件
│   ├── screenshots/                # 失败截图
│   └── tests/
│       ├── conftest.py             # --env/--headed 与 browser_context_args
│       ├── ui_base_test.py         # UI 测试基类（Playwright 生命周期）
│       ├── test_view_operations.py # 与基类匹配的示例用例
│       └── test_*.py               # 其余用例（模板/历史，见 §10）
│
├── common/                         # ---------- 公共层 ----------
│   ├── base_test.py                # 测试基类：生命周期 + 断言代理 + 日志/性能/重试
│   ├── config/settings.py          # Config / TestConfig / CIConfig / EmailConfig
│   ├── context/base_context.py     # Context 抽象基类（API/UI 统一接口）
│   ├── assertions/base_assertion.py# 通用硬断言 + 软断言
│   ├── decorator/
│   │   ├── endpoint_decorator.py   # @with_endpoint / @auto_endpoint / Endpoint.*
│   │   ├── wait_decorator.py       # @poll_until / @wait_for_condition / @wait_for_response
│   │   └── webhook_decorator.py    # @wait_for_webhook
│   ├── utils/
│   │   ├── logger.py               # 控制台 + 文件 + Allure 三通道日志
│   │   ├── allure_helper.py        # Allure/APIAllure/UIAllure/Step/Dynamic 辅助类
│   │   ├── performance_monitor.py  # 性能指标采集与 Allure 附件
│   │   ├── structure_validator.py  # webhook 结构比对
│   │   ├── email_sender.py         # 邮件报告
│   │   ├── visual_test.py、webgl_helper.py、model_stats.py、transform_helper.py、
│   │   │   action_logger.py、helpers.py、cerebars.py（工具类/实验代码）
│   │   ├── data_utils/             # 数据驱动引擎
│   │   │   ├── data_handle.py      # ${...} 占位符解析
│   │   │   ├── data_loader.py      # 另一套 TestDataLoader（历史）
│   │   │   ├── yaml_loader.py      # YamlLoader + load_config（带缓存）
│   │   │   ├── faker_handle.py     # 测试数据生成
│   │   │   ├── glob_data.py、add_data.py（历史全局变量工具）
│   │   └── webhook_utils/
│   │       ├── webhook_listener.py # 轮询 webhook server 拉事件
│   │       ├── webhook_record.py   # SQLite 存取事件基线
│   │       ├── webhook_server.py   # Flask 接收端（依赖外部 models 模块）
│   │       └── webhook_data.db
│   ├── logs/                       # 按日期命名的日志
│   └── wait/                       # 空包
│
├── files/                          # 测试模型（stp/step/obj/dxf/dwg/stl/3mf）
├── allure-results / allure-report  # 报告产物（部分已入库）
├── venv/                           # 虚拟环境（已入库/未忽略）
└── .idea/                          # PyCharm 配置
```

### 2.2 分层职责

| 层 | 目录/文件 | 职责 | 代表 |
| --- | --- | --- | --- |
| 入口层 | `run_*.py`、测试文件 `__main__` | 组装命令行、跑 pytest、生成报告、发邮件 | `run_tests.py` |
| 用例层 | `api/tests`、`ui/tests` | 只做流程编排 + 断言；不写底层操作 | `test_analysis.py`、`test_view_operations.py` |
| 业务层 | `api/endpoints`、`ui/methods` | 把接口/页面动作封装成业务方法 | `AnalysisEndpoints`、`ViewMethods` |
| 上下文层 | `api/core/api_context.py`、`ui/context/ui_context.py` | 生命周期、会话/页面、登录、导航 | `APIContext`、`UIContext` |
| 基础操作层 | `common/base_test.py`、`ui/pages/base_page.py` | 原子操作、断言代理、日志/性能 | `BaseTest`、`BasePage` |
| 断言层 | `common/assertions`、`api/assertions`、`ui/assertions` | 通用/API/UI 断言 | `BaseAssertion` |
| 公共能力层 | `common/utils` | 日志、Allure、数据、配置、性能、webhook | `logger.py` |
| 数据/配置层 | `api/data`、`ui/locators`、`common/config` | 用例数据、接口路径、选择器、环境参数 | `analysis_test_data.yaml` |
| 资源/产物 | `files`、`ui/screenshots`、`common/logs`、`allure-*` | 模型、截图、日志、报告 | — |

### 2.3 调用关系

**API 线：**

```text
test_analysis.py
  └─ fixture: endpoints(api)            # api/tests/conftest.py
       └─ AnalysisEndpoints(ctx)
            └─ APIContext.request(...)  # api/core/api_context.py
                 ├─ requests.Session + Retry
                 ├─ AuthManager.get_auth_header()   # 自动带 Bearer
                 ├─ allure.attach 请求/响应
                 └─ 记录 _last_request / _last_response
  └─ WebhookListener(...).wait_for_id(file_id)
       └─ GET {webhook_server}/history/{file_id} 轮询
            └─ StructureValidator 与 SQLite 基线比对
```

**UI 线：**

```text
test_*.py
  └─ UIBaseTest.setup_class()
       ├─ sync_playwright → chromium → BrowserContext → Page
       └─ UIContext(page)
            ├─ BasePage(page) + main_page_locators.yaml
            ├─ BaseMethods / ViewMethods / MeasurementMethods / ToolbarMethods
            └─ navigate() → upload_model() → wait_for_model_load()
  └─ UIBaseTest.setup_method()
       └─ UIAssertion(page, screenshot_callback)
  └─ teardown_method()
       └─ PerformanceMonitor.attach_to_allure()
```

**数据流：**

```text
analysis_test_data.yaml
  └─ api.data.analysis_test_data.TestDataLoader
       └─ DataHandle.process_data()  # 替换 ${...}
            └─ FileUploadRequest(dataclass)
                 └─ get_all_cases() / get_cases_by_group()
                      └─ @pytest.mark.parametrize("case", ...)
                           └─ case.to_api_params() → AnalysisEndpoints
```

**配置流：**

```text
pytest 命令行(--env/--api-timeout/--api-auto-login) ─┐
环境变量(API_AUTO_LOGIN/WEBHOOK_*/...) ───────────────┼─→ common/config/settings.py::Config
代码内默认值 ────────────────────────────────────────┘

api/data/api_config.yaml ─ YamlLoader.load_config() ─→ AnalysisEndpoints._get_endpoint()
ui/locators/*.yaml       ─ BasePage.load_locators() ─→ get_element("main_page", "file_input")
```

### 2.4 分层特点与规则

1. **方向正确**：`api/ui` 依赖 `common`，`common` 不反向依赖；`tests` 依赖框架层，不直接写 `requests`/`page.locator`（设计意图）。
2. **UI 业务动作按能力域拆文件**：视图、测量、工具栏、批注、Canvas、模型信息各一个 `*_methods.py`，均继承 `BaseMethods`，共享 iframe/Canvas/鼠标能力。
3. **API 业务动作按领域拆文件**：一个领域一个 `*_endpoints.py`，一个 context 注入全部 endpoint。
4. **基类位置不对称**：`UIBaseTest` 放在 `ui/tests/`，`APIBaseTest` 放在 `api/core/`；两者本可都放 `api|ui/tests` 或都放 `api|ui/core`。
5. **公共层按领域再分子包**：`data_utils/`、`webhook_utils/`，但同层还散落着大量单文件工具（`allure_helper`、`logger`、`performance_monitor` 等）。
6. **配置全部 YAML 化**：接口路径、选择器、测试数据均 YAML；环境参数走 `Config` 类。
7. **同时保留多套同类实现**：两套 `TestDataLoader`、两套 webhook listener、三套配置加载入口、两套断言代理路径，是后续维护的主要成本来源（详见 §10）。

---

## 3. 命名风格

### 3.1 目录与文件

| 对象 | 规则 | 示例 |
| --- | --- | --- |
| 目录 | 全小写、单数、领域名 | `api/`、`ui/`、`common/`、`core/`、`endpoints/`、`assertions/`、`methods/`、`locators/` |
| Python 文件 | `snake_case`，**按角色加后缀** | `api_context.py`、`view_methods.py`、`analysis_endpoints.py`、`base_assertion.py`、`data_handle.py`、`yaml_loader.py` |
| 基类文件 | `base_*.py` | `base_test.py`、`base_page.py`、`base_methods.py`、`base_assertion.py` |
| 测试文件 | `test_*.py` | `test_analysis.py`、`test_view_operations.py` |
| YAML | 按用途 | `api_config.yaml`、`analysis_test_data.yaml`、`main_page_locators.yaml` |
| 入口脚本 | `run_*.py` | `run_tests.py`、`run_case.py` |

### 3.2 类

PascalCase，**类名后缀表达角色**：

| 后缀 | 含义 | 示例 |
| --- | --- | --- |
| `Context` | 生命周期/环境 | `APIContext`、`UIContext`、`BaseContext` |
| `Endpoints` | 一组接口 | `AnalysisEndpoints` |
| `Methods` | 一组页面动作 | `ViewMethods`、`MeasurementMethods`、`IFrameMethods` |
| `Page` | 页面原子操作 | `BasePage` |
| `Assertion` | 断言器 | `BaseAssertion`、`APIAssertion`、`UIAssertion` |
| `Test` | 测试基类 | `BaseTest`、`APIBaseTest`、`UIBaseTest` |
| `Helper` / `Manager` / `Loader` / `Listener` / `Monitor` / `Validator` / `Record` | 工具角色 | `AllureHelper`、`AuthManager`、`TestDataLoader`、`WebhookListener`、`PerformanceMonitor`、`StructureValidator`、`WebhookRecord` |
| `TestXxx` | 测试类 | `TestAnalysisEndpoints`、`TestViewOperations`、`TestMeasurement` |
| dataclass | 数据模型 | `FileUploadRequest`、`TestGroup`、`EventCompareResult`、`PerformanceMetric` |

### 3.3 方法/函数

- 一律 `snake_case`，**动词或动词+名词**：`analysis_upload_file`、`get_status_by_id`、`assert_json_path`、`soft_assert_true`、`wait_for_id`、`click_tool`、`measure_distance`。
- 私有方法/内部函数单下划线：`_create_session`、`_get_endpoint`、`_on_fail`、`_attach_to_allure`、`_extract_event_id`。
- 类方法/模块级便捷函数：`get_all_cases`、`get_cases_by_group`、`get_parametrize_data`、`load_config`、`reload_loader`。
- 断言统一 `assert_*` / `soft_assert_*` 前缀；等待统一 `wait_for_*` / `wait_until`；获取统一 `get_*`；判断统一 `is_*`。
- 布尔返回值方法通常以 `is_`、`has_` 开头或直接动词（`click_tool` 返回 bool）。

### 3.4 变量与常量

- 实例属性 `snake_case`：`self.base_url`、`self.ctx`、`self.page`、`self.base_page`、`self.perf`、`self.assertion`。
- 对外别名短小：`self.api`、`self.ui`、`self.analysis`、`self.webhook`。
- API 参数在**边界处转驼峰**：Python 侧 `preview_type`，发送时 `previewType`；映射写在 `FileUploadRequest.to_api_params()` 与 `AnalysisEndpoints.analysis_upload_file()` 的 `param_mapping`。
- 常量 `UPPER_SNAKE` 集中在 `Config` / `EmailConfig`：`API_BASE_URL`、`WEBHOOK_TIMEOUT`、`TEST_FILES_DIR`。
- pytest fixture 用名词：`api_context`、`api`、`endpoints`、`test_data`、`admin_user`、`browser_context_args`。

### 3.5 测试用例命名

- 方法：`test_<行为>[_<条件>]`，如 `test_rotate_view`、`test_upload_with_webhook_wait`、`test_view_operations_performance`。
- 类：`Test<被测功能>`，如 `TestAnalysisEndpoints`、`TestViewOperations`、`TestWorkflow`。
- 参数化用例的人读名称不走方法名，而走 **case 的 `name` 字段**：
  - `ids=get_case_display_name`，`extra_info` 非空时拼成 `"用例名 - 扩展信息"`（`api/tests/test_analysis.py:14`）。
  - 运行时再 `allure.dynamic.title(f"【{case.name}】测试")`。
- 每个测试方法都有中文 docstring，内容会被 `BaseTest.setup_method()` 自动塞进 Allure description。
- marker 用小写单词：`@pytest.mark.api`、`smoke`、`slow`、`webhook`。

### 3.6 YAML / 配置命名

- 接口配置按「域.动作」：`analysis.upload_file`、`analysis.file_by_id`（`api/data/api_config.yaml`）。
- 定位器按「页面/区域.元素」：`main_page.file_input`、`main_page.model_loading`。
- 测试数据：分组名英文（`standard`/`boundary`/`combination`/`regression`/`negative`），用例名中文（`"标准上传-默认参数"`），字段名英文 snake_case（`file_name`、`preview_type`、`need_business_service`）。
- Webhook 事件字典 `enevts.yaml` 用中文一级 key、英文事件 ID 值。

### 3.7 注释与文档

- 文件头部有路径注释（很多与实际路径不一致，见 §10）。
- 分节使用中文 banner：`# ==================== 请求方法 ====================`。
- 函数 docstring 中文，常用 `Args:` / `Returns:` 风格；示例代码放在 docstring 中。
- 日志大量使用 emoji 前缀：`🚀`、`✅`、`❌`、`📤`、`📥`、`📸`、`🧹`。

### 3.8 现有命名不一致（仅记录）

| 类型 | 示例 |
| --- | --- |
| 文件头注释与真实路径不符 | `api/core/base_api.py` 头写 `common/webhook_listener.py`；`api/core/api_base_test.py` 头写 `api/tests/base_test.py`；`ui/context/ui_context.py` 头写 `context/api_context.py`；`ui/tests/ui_base_test.py` 头写 `tests/api_base_test.py` |
| 类名与文件名不一致 | `iframe_methods.py` 里的类叫 `IFrameMethods`；`measure_methods.py` 里的类叫 `MeasurementMethods`；`test_canvs.py`（拼写错误） |
| 同类概念多套命名 | 断言 `assert_is_not_none` vs 测试里写的 `assert_not_none`；`assert_success` vs `assert_business_success`；`wait_for_model_load` vs `wait_for_canvas_ready` |
| 拼写问题 | `enevts.yaml`（events）、`cerebars.py`（celery?）、`test_canvs.py`（canvas） |
| 同名类重复 | `TestDataLoader` 同时存在于 `api/data/analysis_test_data.py` 和 `common/utils/data_utils/data_loader.py`；`WebhookListener` 同时存在于 `api/core/base_api.py` 和 `common/utils/webhook_utils/webhook_listener.py` |
| 测试类重名 | `TestViewOperations` 同时在 `ui/tests/test_design.py` 和 `ui/tests/test_view_operations.py` 中出现 |

---

## 4. 请求封装方式

### 4.1 分层结构

```text
测试用例
  └─ endpoints fixture（api/tests/conftest.py）
       └─ AnalysisEndpoints（api/endpoints/analysis_endpoints.py）
            └─ APIContext（api/core/api_context.py）
                 ├─ requests.Session
                 ├─ AuthManager（api/core/auth_manager.py）
                 └─ Allure 附件
```

- **不直接使用 requests**：用例和 endpoint 都通过 `APIContext` 发请求。
- **端点路径不下硬编码**：统一读 `api/data/api_config.yaml`。
- **认证不写在 endpoint**：`APIContext.request()` 自动注入 Authorization 头。
- **返回值保持原始 `requests.Response`**：由 endpoint 自己 `response.json()` 并做业务判断。

### 4.2 `APIContext`（`api/core/api_context.py`）

职责：管理 `requests.Session`、发送请求、记录历史、把请求/响应挂到 Allure、把认证委托给 `AuthManager`。

关键点：

1. **构造**
   - `base_url` 默认 `Config.API_BASE_URL`，`timeout` 默认 `Config.API_TIMEOUT`。
   - 默认请求头只有 `Accept: application/json`。
   - 初始化 `AuthManager`、`APIAllureHelper`（后者创建了但实际未使用）。

2. **Session 与重试**（`_create_session`）
   ```python
   retry_strategy = Retry(
       total=Config.API_MAX_RETRIES,      # 3
       backoff_factor=0.5,
       status_forcelist=[500, 502, 503, 504]
   )
   adapter = HTTPAdapter(max_retries=retry_strategy)
   self.session.mount("http://", adapter)
   self.session.mount("https://", adapter)
   ```

3. **统一请求入口** `request(method, endpoint, files, data, json_data, params, headers, **kwargs)`
   - URL 拼接：`f"{self.base_url}{endpoint}"`。
   - Header 合并：`session.headers` + 调用方额外 headers。
   - 文件上传时移除 `Content-Type`，交给 requests 自动生成 boundary。
   - **自动认证**：`if Config.TOKEN_URL not in endpoint:` 时调用 `AuthManager.get_auth_header()`，登录接口自身不带 token。
   - 默认超时：调用方未传 `timeout` 时用 `Config.API_TIMEOUT`。
   - 记录 `_last_request`（method/url/headers/params/has_files；**不记录 body**）。
   - 发送后记录 `_last_response`、耗时、请求历史（历史里保存的是 Response 对象）。
   - 调用 `_attach_to_allure()` 附上「请求信息」「响应信息」两个 TEXT 附件。

4. **便捷方法**
   - `get(endpoint, params=...)`
   - `post(endpoint, data=..., json=...)`（注意内部参数名是 `json_data`）
   - `post_file(endpoint, file_path, data=...)`：以 `files={'file': (basename, fh, 'application/octet-stream')}` 上传，结束后关闭文件句柄。
   - `put/delete/patch`
   - `set_header(s)`、`set_auth_token()`、`clear_auth_token()`
   - `navigate(url)`：API 语境下等价于「切换 base_url」
   - `wait_for(condition, timeout)`：字符串→轮询接口可访问；callable→轮询条件
   - `health_check(endpoint="/health")`
   - `get_last_request()`、`get_last_response()`、`get_last_response_json()`、`clear_history()`

5. **特点**
   - 不做 `raise_for_status()`，HTTP 4xx/5xx 不自动抛异常，交给断言层判断。
   - 响应时间用 `time.time()` 自己算，不依赖 `response.elapsed`。
   - 失败时的请求/响应附件由测试基类/断言器补挂（`APIBaseTest._on_assert_fail_screenshot`、`conftest.pytest_runtest_makereport`）。

### 4.3 `AuthManager`（`api/core/auth_manager.py`）

- 职责单一：只处理 token。
- 缓存 + 过期判断：`expires_in - 60` 秒作为安全边界。
- 获取方式：
  ```python
  GET {base_url}{Config.TOKEN_URL}
  params = {"app_id": Config.APP_ID, "app_secret": Config.APP_SECRET}
  ```
- 期望响应：`{"code": 200, "data": {"access_token": "...", "expires_in": 7200}}`
- `get_auth_header()` 自动补 `Bearer ` 前缀；token 本身带前缀则不重复添加。
- 注：token 明文写日志（`self.logger.info(self._access_token)`）。

### 4.4 `AnalysisEndpoints`（`api/endpoints/analysis_endpoints.py`）

- 构造时可注入 `api_context`，也可只给 `base_url`。
- 路径配置：
  ```python
  project_root = Path(__file__).parent.parent.parent
  config_path = project_root / "api" / "data" / "api_config.yaml"
  self.api_config = load_config(str(config_path))   # YamlLoader
  ```
- `_get_endpoint(key)`：从 YAML 读路径，缺失则 `ValueError`。
- **参数命名转换**：Python snake_case → API camelCase，映射表内置在方法里；同时兼容调用方直接传 camelCase。
  ```python
  param_mapping = {
      'webhook_key': 'webhookKey',
      'use_cache': 'useCache',
      'preview_type': 'previewType',
      'need_business_service': 'needBusinessService',
      ...
  }
  ```
- **文件上传** `analysis_upload_file(file_path, **kwargs)`：
  - 校验文件存在；
  - 过滤 `None` / `""`；
  - `ctx.post_file(...)`；
  - 解析响应，成功判断 `result.get('code') != '200' and result.get('success') is not True`；
  - file_id 兼容 `id` / `fileId` / `file_id`；
  - 返回 `{'file_id', 'file_name', 'response'}`。
- **链接上传** `analysis_upload_filepath(...)`：组 `{filePath, fileType, fileName}` 走 `ctx.post(json=...)`。当前实现里 `kwargs` 分支引用了未定义的 `mapping`，且实际签名与测试调用参数名不一致（详见 §10）。
- **查询**：`get_status_by_id(file_id)` → `analysis.file_by_id`；`get_result_by_page(file_id)` → `analysis.get_result`（配置文件中不存在该 key）。

### 4.5 测试侧装配（`api/tests/conftest.py`）

```python
@pytest.fixture(scope="session")
def api_context():
    ctx = APIContext(Config.API_BASE_URL)
    ctx.setup()
    if Config.API_AUTO_LOGIN:
        ctx.ensure_token()
        token = ctx.get_access_token()
        ctx.set_auth_token(token)      # 同时写入 session 头，属于双保险
    yield ctx
    ctx.teardown()

@pytest.fixture
def endpoints(api):
    class Endpoints:
        def __init__(self, ctx):
            self._analysis = AnalysisEndpoints(ctx)
        @property
        def analysis(self): return self._analysis
    return Endpoints(api)
```

用例里：

```python
class TestAnalysisEndpoints:
    @pytest.fixture(autouse=True)
    def setup(self, endpoints):
        self.analysis = endpoints.analysis
        self.webhook = WebhookListener(Config.WEBHOOK_BASE_URL)

    def test_all_cases(self, endpoints, case):
        result = endpoints.analysis.analysis_upload_file(
            file_path=Config.get_test_file_path(case.file_name),
            **case.to_api_params()
        )
        assert result.get('file_id') is not None
```

### 4.6 异步结果（Webhook）获取

3D 解析是异步任务，上传拿到 `file_id` 后通过 webhook 服务确认识别结果：

- 服务端地址：`Config.WEBHOOK_BASE_URL`（默认 `http://47.94.122.228:5000`）。
- 客户端 `common/utils/webhook_utils/webhook_listener.py` 用**轮询 GET**，不是长连接：
  - `GET /history/{file_id}`：拉该文件全部事件；
  - `GET /latest/{file_id}`：拉最新事件；
  - `wait_for_id(file_id, timeout)`：轮询直到超时，返回 `(records, compare_results)`；
  - `wait_for_specific_event(file_id, event_id, timeout)`；
  - `wait_for_any_event(file_id, timeout)`。
- 事件字段提取路径固定：
  - 事件名：`payload.serviceInfo.event`
  - 文件 ID：`payload.data.id`
  - 文件名：`payload.data.fileName`
- 结构校验：`StructureValidator` 对比历史基线（SQLite `webhook_data.db`），返回 `EventCompareResult`，可输出缺失/新增字段。
- 还有一份更简单的 `WebhookListener` 放在 `api/core/base_api.py`（读 `/history` 全量、用 `_last_total` 游标），与正式版命名相同但接口不同。

### 4.7 请求封装的风格总结

| 维度 | 做法 |
| --- | --- |
| 会话 | 一个 session 级 `APIContext`，全测试会话复用 |
| 重试 | 只对 5xx/连接错误生效，3 次，0.5 退避 |
| 认证 | 自动注入，登录接口排除；token 由独立 manager 缓存 |
| 路径 | YAML 集中管理，endpoint 层做 key → path 查找 |
| 参数 | 用例层用 Python 风格，边界处统一转 camelCase |
| 返回值 | 原始 Response + endpoint 包装后的业务字典 |
| 可观测性 | 每个请求自动挂 Allure 请求/响应附件；失败再补 last request/response |
| 错误处理 | HTTP 错误不抛；业务错误由 endpoint 抛 `Exception`；文件不存在抛 `FileNotFoundError` |

---

## 5. 断言写法

### 5.1 三层结构

```text
BaseTest（测试基类）
  ├─ self.assert_xxx()  ──代理──▶ BaseAssertion（通用断言）
  ├─ self.soft_assert_xxx() ─────▶ BaseAssertion 软断言
  └─ 子类替换为：
       ├─ APIBaseTest  → APIAssertion（HTTP/JSON）
       └─ UIBaseTest   → UIAssertion（元素/页面/Canvas）
```

### 5.2 `BaseAssertion`（`common/assertions/base_assertion.py`）

- 构造时接收 `screenshot_callback`（失败截图钩子）与内部 `_errors`（软断言错误列表）。
- **硬断言**：失败时 `_on_fail()` → 记录日志 + 挂 Allure 文本 + 可选截图 → `raise AssertionError`。
  - 覆盖：真/假、相等/不等、None、成员、类型、大小比较、区间、字符串包含/前后缀、正则。
  - 每个具体断言最终都落到 `assert_true(condition, message)`，默认消息为中文，例如：
    - `assert_equal`：`期望 'x', 实际 'y'`
    - `assert_between`：`{value} 应在 [min, max] 之间`
- **软断言**：`soft_assert_true` / `soft_assert_equal`，失败只收集不中断；`assert_all()` 在用例末尾统一抛 `AssertionError`（消息里带错误条数）。
- `_on_fail` 的截图回调只对硬断言触发（`not is_soft`）。

典型写法：

```python
self.assert_true(result, "旋转操作应该成功")
self.assert_equal(actual, expected, f"状态码断言失败: 期望 {expected}")
self.assert_between(value, 0, 100)
self.soft_assert_true(cond, "字段 A 应存在")
self.soft_assert_equal(a, b)
self.assert_all()
```

### 5.3 `APIAssertion`（`api/assertions/api_assertion.py`）

在通用断言之上扩展 HTTP/JSON：

| 方法 | 说明 |
| --- | --- |
| `assert_status_code(response, expected)` | 断言 HTTP 状态码，并挂 Allure 文本 |
| `assert_success(response)` | 2xx |
| `assert_client_error` / `assert_server_error` | 4xx / 5xx |
| `assert_json_path(response, "data.id", expected)` | 点号路径取值后比较；支持 list 下标；列表 + 非数字 key 时返回列表投影 |
| `assert_json_contains` / `assert_json_not_contains` | 顶层 key 存在性 |
| `assert_json_length(response, "data.list", n)` | 数组长度 |
| `assert_response_header` | 响应头存在/相等 |
| `assert_response_time` | 基于 `response.elapsed` 的毫秒阈值 |
| `assert_schema` | 可选依赖 `jsonschema` |
| `assert_business_code(response, 200, "code")` | 业务状态码 |

### 5.4 `UIAssertion`（`ui/assertions/ui_assertion.py`）

- 构造时持有 `Page`，所有断言接受 **selector 字符串**（不是 YAML key）。
- 元素：可见/隐藏/存在/数量/文本（精确或包含）/属性/勾选/启用/聚焦。
- 页面：`assert_title`、`assert_url`、`assert_url_contains`。
- 三维专用：`assert_canvas_exists`、`assert_webgl_context`、`assert_model_loaded`、`assert_fps_greater_than`。
- 视觉回归：`assert_screenshot_match` 目前只做「首次创建 baseline + 挂截图」，**没有真正的像素对比**。

### 5.5 `BaseTest` 与子类的代理

- `BaseTest` 暴露同名 `assert_*`/`soft_assert_*`，内部转发 `self.assertion`。
- `APIBaseTest.setup_method()` 把断言器替换为 `APIAssertion`，并加便捷方法：
  - `self.assert_status(response, 200)`
  - `self.assert_json_path(response, "code", 200)`
  - `self.assert_business_success(response)`
- `UIBaseTest.setup_method()` 替换为 `UIAssertion`，并提供 `self.ui` 别名和一批 UI 断言转发。
- 用例中常见的三种写法并存：
  1. 基类断言：`self.assert_true(...)` / `self.assert_performance(...)`
  2. 原生断言：`assert result is not None` / `assert count > 0`
  3. 预期异常：`with pytest.raises(FileNotFoundError): ...`
- 失败时的失败信息除了 `AssertionError` 消息，还会带：
  - 断言器挂的「断言失败 - ...」TEXT 附件；
  - 测试基类 `_on_assert_fail_screenshot` 的截图/最后请求响应；
  - `conftest.pytest_runtest_makereport` 再补一份最后请求/响应。

### 5.6 断言风格总结

| 场景 | 推荐写法（工程既有风格） |
| --- | --- |
| 通用条件 | `self.assert_true(cond, "中文描述")` |
| 值相等 | `self.assert_equal(actual, expected, "期望 X 实际 Y")` |
| 存在性 | `self.assert_is_not_none(value, "xxx 不应为空")` |
| 数值范围 | `self.assert_between(v, min, max)` |
| 性能 | `self.assert_performance(duration_ms, 500, "旋转视图")` |
| API 状态 | `self.api_assert.assert_status_code(resp, 200)` 或 `self.assert_status(resp, 200)` |
| API 业务字段 | `self.api_assert.assert_json_path(resp, "data.id", expected)` |
| UI 元素 | `self.ui.assert_element_visible("canvas")` 或 `self.assert_element_visible(...)` |
| 多字段校验 | 多条 `soft_assert_*` + 末尾 `self.assert_all()` |
| 预期异常 | `with pytest.raises(Exception): ...` |

### 5.7 断言相关缺口（仅记录）

- `BaseTest` 代理了 `assert_greater_equal`、`assert_less_equal`、`assert_not_contains`、`assert_empty`、`assert_not_empty`、`has_soft_assert_failures`、`soft_assert_in`、`soft_assert_greater`、`soft_assert_less`，但 `BaseAssertion` **没有定义这些方法**，调用会 `AttributeError`（`common/base_test.py:168-225`）。
- 多个 UI 测试调用 `self.assert_not_none(...)`，基类只有 `assert_is_not_none`。
- `UIBaseTest` 代理 `soft_assert_element_visible` / `soft_assert_element_text`，`UIAssertion` 未实现。
- `UIAssertion.assert_element_hidden` 在元素实际可见时，`wait_for_selector(state="hidden")` 会超时，异常分支直接 `assert_true(True)`，语义上可能把「应隐藏却可见」判为通过。

---

## 6. Allure 装饰器用法

### 6.1 静态装饰器（报告分组骨架）

典型写法（API 用例）：

```python
@allure.epic("CNC平台")          # 类：业务线
@allure.feature("零件解析")       # 类：功能模块
class TestAnalysisEndpoints:

    @allure.story("全量测试")      # 方法：用户故事/场景
    @pytest.mark.parametrize("case", get_all_cases(), ids=get_case_display_name)
    def test_all_cases(self, endpoints, case):
        ...

    @allure.title("测试：上传不存在的文件")   # 方法：单条用例标题
    @allure.story("异常测试")
    @pytest.mark.api
    def test_upload_file_not_found(self):
        ...
```

典型写法（UI 用例）：

```python
@allure.feature("视图操作")
@allure.severity(allure.severity_level.CRITICAL)
class TestViewOperations(UIBaseTest):

    @allure.story("旋转视图")
    def test_rotate_view(self):
        ...
```

各文件的使用矩阵：

| 文件 | epic | feature | severity | story | title | 参数化 ids |
| --- | --- | --- | --- | --- | --- | --- |
| `api/tests/test_analysis.py` | 类 | 类 | — | 方法 | 部分方法 | ✅ |
| `ui/tests/test_view_operations.py` | — | 类 | 类 | 方法 | — | — |
| `ui/tests/test_measure.py` | — | 类 | — | 方法 | — | — |
| `ui/tests/test_annotation.py` | — | 类 | — | 方法 | ✅ | — |
| `ui/tests/test_canvs.py` | — | 类 | — | 方法 | — | — |
| `ui/tests/test_design.py` | — | 方法 | — | 方法 | — | — |
| `ui/tests/test_workflow.py` | — | 类 | — | 方法 | — | — |
| `ui/tests/test_performance.py` | — | 类 | — | 方法 | — | — |
| `ui/tests/test_coverage.py` | — | 类 | — | 方法 | — | — |
| `ui/tests/test_model_viewer.py` | — | — | — | — | — | — |

### 6.2 动态 API（`allure.dynamic`）

数据驱动用例无法用静态 `@allure.title` 表达每条数据，因此运行期设置：

```python
allure.dynamic.title(f"【{case.name}】测试")
allure.dynamic.description(f"""
### 测试用例详情
- 用例名称: {case.name}
- 文件名: {case.file_name}
- 预览格式: {case.preview_type}
...
""")
```

`common/utils/allure_helper.py::AllureDynamicHelper` 又封装了一层：

| 方法 | 对应 allure API |
| --- | --- |
| `set_title` | `allure.dynamic.title` |
| `set_description` | `allure.dynamic.description` |
| `set_feature` / `set_story` | `allure.dynamic.feature/story` |
| `set_severity` | 字符串 → `severity_level` 枚举 → `allure.dynamic.severity` |
| `set_tag` / `set_tags` | `allure.dynamic.tag` |
| `set_link` | `dynamic.link/issue/testcase` |
| `set_parameters` | `allure.dynamic.parameter` |

`BaseTest` 也提供了 `add_tag`、`set_priority`、`set_feature`、`set_story` 等转发方法。

### 6.3 步骤（`allure.step`）

两种写法：

```python
with allure.step("上传文件"):
    result = endpoints.analysis.analysis_upload_file(...)
    allure.attach(f"file_id: {file_id}", "上传结果", allure.attachment_type.TEXT)

with allure.step("等待 Webhook 回调"):
    records, compare_results = webhook.wait_for_id(file_id=file_id, timeout=Config.WEBHOOK_TIMEOUT)
```

`StepHelper`（`common/utils/allure_helper.py:286`）封装了：

- `step(title)`：装饰器，内部 `with allure.step(title): return func(...)`；
- `log_step(message)`：只调用 `allure.step(message)`，**没有作为上下文进入**，因此单独调用不会产生步骤；
- `log_step_with_attachment(message, content, name)`：自带 `with`。

`UIBaseTest` 中把 `self.step = StepHelper()`，但 `test_view_operations.py:85` 写成 `with self.step.log_step(...)`，而 `log_step` 返回 `None`，会报错（详见 §10）。

### 6.4 附件（`allure.attach`）

工程里附件使用非常密集，分为几类：

| 来源 | 内容 | 类型 |
| --- | --- | --- |
| `APIContext._attach_to_allure` | 每个请求的「请求信息」「响应信息」 | TEXT |
| `APIBaseTest._on_assert_fail_screenshot` | 失败时最后请求 JSON / 响应体 | JSON / TEXT |
| `conftest.pytest_runtest_makereport` | 失败时响应体、请求行 | TEXT |
| `BaseAssertion._on_fail` | 断言失败消息 | TEXT |
| `APIAssertion` | 状态码验证、JSON 断言详情 | TEXT |
| `TestLogger` | **每一条 info/success/error/warning/step/section 日志** | TEXT |
| `UIBaseTest.take_failure_screenshot` / `take_screenshot` | 页面截图 | PNG |
| `UIAssertion.assert_screenshot_match` | 截图（含 baseline 写入） | PNG |
| webhook 测试 | 事件列表、结构差异、解析结果 | TEXT |
| `PerformanceMonitor.attach_to_allure` | 性能指标表 | TEXT/JSON |

常用类型：`allure.attachment_type.TEXT`、`.JSON`、`.PNG`；辅助类还封装了 HTML/XML/CSV。

附件命名统一用中文描述，例：`请求信息`、`响应信息`、`失败截图_xxx`、`断言失败 - xxx`、`解析结果`、`结构变化分析`。

### 6.5 封装类

| 类 | 用途 | 使用情况 |
| --- | --- | --- |
| `AllureHelper` | 通用 attach：text/json/html/xml/csv/image/file/log | 少量/未广泛使用 |
| `APIAllureHelper` | 请求/响应附件 + header 脱敏（token 截断） | `APIContext` 创建了实例但未调用 |
| `UIAllureHelper` | 截图、页面源码、元素截图、console、性能 | `UIBaseTest` 创建了实例，少量调用 |
| `StepHelper` | step 装饰器 / 步骤日志 | UI 基类使用 |
| `AllureDynamicHelper` | 动态 title/feature/story/severity/tag/link/parameter | UI 基类使用 |

### 6.6 运行与报告生成

- `pytest.ini` 的 `addopts` 已带 `--alluredir=allure-results`。
- 各测试文件 `__main__` 里会：
  ```python
  pytest.main([__file__, "-v", "-s", "--tb=short",
               f"--alluredir={allure_results_dir}", "--clean-alluredir"])
  os.system(f"allure generate {allure_results_dir} -o {allure_report_dir} --clean")
  ```
- `run_tests.py` / `run_tests_with_allure.py` 也用 `allure generate`，后者还起 `http.server` 供局域网访问并发送邮件。
- 环境信息本应在 `api/tests/conftest.py::pytest_configure` 通过 `allure.dynamic.environment(...)` 写入，但该函数被同名函数覆盖，实际不生效（见 §10）。

---

## 7. 数据驱动方式

### 7.1 数据文件

主数据源：`api/data/analysis_test_data.yaml`

结构：

```yaml
groups:
  - name: "standard"
    description: "标准功能测试"
    cases:
      - name: "标准上传-默认参数"
        file_name: "${getfile:${global:test_files_dir}:3mf,stp}"
        extra_info: "测试默认参数 | ${datetime_now}"
        expected_status: "success"

      - name: "预览格式-glb"
        file_name: "${getfile:${global:test_files_dir}:stp}"
        preview_type: "0"
        expected_status: "success"
```

分组共 5 类：`standard`、`boundary`、`combination`、`regression`、`negative`；冒烟用例通过跨组取 `standard + boundary` 实现。

### 7.2 加载链路

1. `TestDataLoader.__init__` 定位 YAML（同目录）和工程根目录（找 `.git`）。
2. `_load()`：
   - `yaml.safe_load` 读原始数据；
   - 延迟实例化 `DataHandle`，并设置全局变量：
     - `test_files_dir` = `<project_root>/files`
     - `webhook_key`
   - `handle.process_data(deepcopy(raw))` 替换所有占位符；
   - 遍历 `groups`，把每个 case 转成 `FileUploadRequest` dataclass，过滤不存在的字段。
3. 模块级单例 + 便捷函数：
   ```python
   get_loader(reload=False)
   get_all_cases(reload=False)
   get_cases_by_group(*names, reload=False)
   get_parametrize_data(*names)
   ```
4. 测试里：
   ```python
   @pytest.mark.parametrize("case", get_all_cases(), ids=get_case_display_name)
   def test_all_cases(self, endpoints, case):
       ...
   ```

### 7.3 case 模型（`FileUploadRequest`）

字段分为三类：

| 类别 | 字段 |
| --- | --- |
| 元信息 | `name`、`expected_status`、`expected_events`、`expect_exception`、`_group`、`_group_description` |
| 文件 | `file_name`、`params`、`webhook_key` |
| API 参数 | `use_cache`、`extra_info`、`preview_type`、`need_business_service`、`need_stl_light_weight`、`minimum_thickness_threshold`、`high_risk_area_define`、`cover_color` |

`to_api_params()` 负责把非空字段转成 API 驼峰名，并保留 `params`。

### 7.4 参数化写法

- `ids=get_case_display_name`：用 case 对象生成可读 ID（`用例名 - extra_info`）。
- 每个测试方法开头统一做：
  1. `allure.dynamic.title(...)`
  2. `allure.dynamic.description(...)`（Markdown 表格式详情）
  3. 取 `file_path`
  4. 若 `expect_exception`，`with pytest.raises(Exception)` 后 return
  5. 正常调用上传并断言 `result is not None`、`file_id is not None`
- 缺点：6 个测试方法几乎完全重复，只是 `parametrize` 的分组不同（`test_all_cases`、`test_standard_cases`、`test_boundary_cases`、`test_combination_cases`、`test_regression_cases`、`test_negative_cases`、`test_smoke_cases`）。

### 7.5 占位符语法（`DataHandle`）

正则：`\$\{([^}]+)\}`，支持嵌套解析。

| 语法 | 作用 | 示例 |
| --- | --- | --- |
| `${global:key}` | 取全局变量 | `${global:test_files_dir}` |
| `${getfile:目录:扩展名列表}` | 从目录递归随机取一个匹配文件 | `${getfile:/path/files:stp,step}` |
| `${listfile:目录:pattern}` | 列出文件 | `${listfile:/path:*.stp}` |
| `${file:路径:格式:key}` | 读 json/yaml/csv/txt 文件内容 | `${file:data.json:json:key}` |
| `${uuid}` | 随机 UUID | — |
| `${timestamp}` / `${datetime_now}` / `${date_today}` | 时间 | `${datetime_now(%Y-%m-%d)}` |
| `${random_int(min,max)}` / `${random_float(...)}` / `${random_string(len)}` / `${random_bool}` / `${random_choice(...)}` | 随机值 | — |
| `${faker:方法(...)}` | FakerData 方法 | `${faker:generate_phone()}` |

- 整个字符串只有一个占位符时，返回原始类型（int/bool/None 等）；多个占位符时做字符串替换。
- 解析失败时原样返回 `${...}`，不会抛异常。
- 内置函数参数支持位置参数与 `key=value` 关键字参数，字符串可用单/双引号。

### 7.6 其他数据工具（目前多为历史/未使用）

| 文件 | 说明 |
| --- | --- |
| `common/utils/data_utils/data_loader.py` | 另一套 `TestDataLoader`，默认读 `model_test/api/data/test.yaml`（本项目不存在），与 `api/data` 的 loader 同名不同实现 |
| `api/data/analysis_test_data.json` | 另一份 JSON 用例（`file_upload_tests`），当前没有代码引用 |
| `api/data/enevts.yaml` | webhook 事件 ID 大小写/中文映射，当前没有代码引用 |
| `common/utils/data_utils/faker_handle.py` | Faker 封装，依赖 `thefuzz`（未在 requirements 中） |
| `common/utils/data_utils/glob_data.py` / `add_data.py` | 用类属性做全局变量，`add_data.py` 使用 `from data_utils...` / `from tools.logger...` 顶层导入，属于其他项目拷贝来的遗留代码 |
| `common/decorator/endpoint_decorator.py` | 接口路径装饰器族，当前 endpoint 未使用 |

### 7.7 数据驱动的风格总结

- **YAML 是唯一事实源**（主链路），dataclass 作为强类型载体。
- **占位符承担动态化**：随机文件、时间戳、UUID、Faker，让同一份 case 每次运行有差异。
- **分组即测试策略**：组名直接映射到测试方法与 marker。
- **参数命名在 dataclass 与 endpoint 两处各转换一次**（Python → 驼峰）。
- 用例数据、接口路径、定位器都在 YAML，但格式与加载器各不相同。

---

## 8. 配置读取方式

### 8.1 总览

| 配置类型 | 载体 | 读取方 | 特点 |
| --- | --- | --- | --- |
| 环境/运行参数 | `common/config/settings.py::Config` | 全项目 | 静态类属性；部分支持环境变量 |
| 命令行参数 | `--env`、`--api-timeout`、`--api-auto-login`、`--headed` | 两个 `conftest.py` | 本意是覆盖 `Config` |
| 接口路径 | `api/data/api_config.yaml` | `YamlLoader.load_config` → `AnalysisEndpoints` | 点号 key；`lru_cache` |
| UI 定位器 | `ui/locators/*.yaml` | `BasePage.load_locators` | 文件级加载；点号 key |
| 测试数据 | `api/data/analysis_test_data.yaml` | `api/data/analysis_test_data.py` | 占位符处理 |
| 邮件 | `EmailConfig` | `email_sender.py` | 明文账号/授权码 |
| 环境变量 | `API_AUTO_LOGIN`、`WEBHOOK_BASE_URL`、`WEBHOOK_KEY`、`WEBHOOK_TIMEOUT` | `Config` | 有默认值 |

### 8.2 `Config`（`common/config/settings.py`）

一个纯静态类，所有配置都是类属性，分块组织：

- **UI**：`HEADLESS`、`SLOW_MO`、视口、截图开关、默认账号、`CI_URL/PROD_URL/TEST_URL/BASE_URL`、超时、截图/日志/报告目录。
- **API**：`API_BASE_URL`、`APP_ID`、`APP_SECRET`、`TOKEN_URL`、`API_AUTO_LOGIN`、`API_TIMEOUT`、`API_MAX_RETRIES`。
- **Webhook**：`WEBHOOK_BASE_URL`、`WEBHOOK_KEY`、`WEBHOOK_TIMEOUT`（后三者支持环境变量）。
- **文件**：`TEST_FILES_DIR` + `get_test_file_path(filename)`。
- **路径推导**：以 `Path(__file__)` 为基准，`PROJECT_ROOT = parent.parent.parent`。

还有两个未使用的环境子类：

```python
class TestConfig(Config):  HEADLESS=False; SLOW_MO=100
class CIConfig(Config):    HEADLESS=True;  SLOW_MO=0
```

读取方式一律 `from common.config.settings import Config`，直接访问类属性。

### 8.3 pytest 命令行参数

`api/tests/conftest.py`：

```python
def pytest_addoption(parser):
    parser.addoption("--env", choices=["dev", "test", "staging", "prod"], default="test")
    parser.addoption("--api-timeout", type=int, default=30)
    parser.addoption("--api-auto-login", action="store_true", default=True)

def pytest_configure(config):
    Config.ENV = config.getoption("--env")
    Config.API_TIMEOUT = config.getoption("--api-timeout")
    Config.API_AUTO_LOGIN = config.getoption("--api-auto-login")
    TestDataLoader.load()
    allure.dynamic.environment(...)
```

`ui/tests/conftest.py`：

```python
def pytest_addoption(parser):
    parser.addoption("--env", default="test")
    parser.addoption("--headed", action="store_true", default=False)

@pytest.fixture(scope="session")
def browser_context_args(request):
    return {"headless": not request.getoption("--headed"), "slow_mo": 300}
```

注意：
- 两个 conftest 都注册 `--env`，若同时被加载会冲突。
- `ui/tests/conftest.py` 的 `browser_context_args` 是 pytest-playwright 的 fixture 名，但依赖里没有 `pytest-playwright`，且 `UIBaseTest` 自己手动起浏览器，因此这个 fixture 未被使用。
- `api/tests/conftest.py` 里定义了两次 `pytest_configure`，**后定义覆盖前定义**，所以环境参数并未真正写入 `Config`，`TestDataLoader.load()` 也不会执行。

### 8.4 接口路径配置

`api/data/api_config.yaml`：

```yaml
auth:
  get_token: "/forface/external/oauth/getAccessToken"
analysis:
  upload_file: "/forface/external/analysis/uploadFile"
  upload_filepath: "/forface/external/analysis/uploadFilePath"
  file_by_id: "/forface/external/analysis/findByFileId"
  file_by_page: "/forface/external/analysis/findByPage"
```

读取：

```python
from common.utils.data_utils.yaml_loader import load_config
self.api_config = load_config(str(config_path))
endpoint = self.api_config.get('analysis.upload_file')
```

- `YamlLoader.get(path)` 按点号逐级 `dict.get`，缺失返回 default。
- `load_config` 用 `@lru_cache(maxsize=20)`，同一路径只读一次。
- `ConfigLoader`（`common/utils/config_loader.py`）是另一套单例加载器，支持多候选路径、`get_endpoint(name, **kwargs)` 路径参数替换，但当前**没有调用方**。

### 8.5 UI 定位器配置

`BasePage.load_locators(file_name)`：

```python
locator_path = Path(__file__).parent.parent / "locators" / file_name
self.locators = yaml.safe_load(f)
```

- `UIContext` 构造时加载 `main_page_locators.yaml`。
- 读取：`get_locator("main_page", "file_input")` → `"input[type=\"file\"]"`；`get_element(...)` 返回 `page.locator(...)`。
- 文件：
  - `main_page_locators.yaml`：主页面上传、加载、iframe、错误提示（约 10 个 key）。
  - `iframe_locators.yaml`、`locators.yaml`：iframe 内/历史选择器。
  - `viewer_locators.yaml`：空文件。
- 不少 `methods/*` 直接写选择器字符串（如 `button:has-text('测量')`、`.fc-tool-btn-box`），没有走定位器 YAML，属于混合风格。

### 8.6 配置优先级（实际）

按代码设计：

```text
环境变量（部分项） > Config 类属性（含代码默认值）
命令行参数（--env/--api-timeout/--api-auto-login）本应覆盖 Config，但因函数被覆盖而未生效
```

按实际运行：

```text
Config 类默认值 / 环境变量
```

### 8.7 配置使用注意点

- 敏感信息直接写在源码：`APP_SECRET`、邮箱授权码、webhook key（`settings.py:60-61`、`98-116`）。
- `API_BASE_URL`、`BASE_URL` 写死生产地址；`--env` 无法真正切换。
- `TestConfig`/`CIConfig` 定义了但没被选用。
- 路径推导依赖文件层级（`parent.parent...`），移动文件后容易失效。
- `ConfigLoader`、`YamlLoader`、`settings.Config` 三套机制并存，新代码容易选错入口。

---

## 9. 照着现有风格写新用例的最小套路

### 9.1 新增一个 API 领域

1. 在 `api/data/api_config.yaml` 增加域：
   ```yaml
   order:
     create: "/forface/external/order/create"
     detail: "/forface/external/order/detail"
   ```
2. 新建 `api/endpoints/order_endpoints.py`：
   ```python
   class OrderEndpoints:
       def __init__(self, api_context=None, base_url=None):
           self.ctx = api_context
           self.base_url = api_context.base_url if api_context else (base_url or Config.API_BASE_URL)
           self.api_config = load_config(str(config_path))

       def _get_endpoint(self, key: str) -> str:
           endpoint = self.api_config.get(key)
           if not endpoint:
               raise ValueError(f"配置中未找到: {key}")
           return endpoint

       def create(self, **kwargs) -> Dict:
           response = self.ctx.post(self._get_endpoint("order.create"), json=kwargs)
           return response.json()
   ```
3. 在 `api/endpoints/__init__.py` 导出，并在 `api/tests/conftest.py` 的 `Endpoints` 工厂里加属性。
4. 测试：
   ```python
   @allure.epic("订单")
   @allure.feature("订单创建")
   class TestOrder:
       @pytest.fixture(autouse=True)
       def setup(self, endpoints):
           self.order = endpoints.order

       @allure.story("创建订单")
       @allure.title("测试：创建订单成功")
       @pytest.mark.api
       def test_create(self):
           with allure.step("调用创建接口"):
               data = self.order.create(...)
           self.assert_is_not_none(data.get("id"), "订单 ID 不应为空")
   ```

### 9.2 新增一个 UI 用例

1. 在 `ui/methods/` 新增能力域（继承 `BaseMethods`），方法是「业务动作 + bool/值返回」，内部用 `get_canvas()`、`mouse_drag()`、`click_button_by_text()` 等。
2. 在 `UIContext.__init__` 里挂载。
3. 测试类继承 `UIBaseTest`：
   ```python
   @allure.feature("剖切")
   class TestSection(UIBaseTest):
       @allure.story("切换隐藏切面")
       def test_toggle_hide_section(self):
           result = self.ctx.section.toggle_hide_section()
           self.assert_true(result, "切换隐藏切面失败")
           self.take_canvas_screenshot("剖切后")
   ```
4. 断言优先用 `self.assert_*`（基类代理），需要软断言时用 `soft_assert_*` + `assert_all()`。
5. 步骤用 `with allure.step("...")` 或 `self.log_info()`；截图用 `self.take_screenshot()` / `self.take_canvas_screenshot()`。

### 9.3 新增一条数据驱动用例

1. 在 `analysis_test_data.yaml` 的某个组追加 case；字段名保持 snake_case。
2. 动态字段用占位符（`${getfile:${global:test_files_dir}:stp}`、`${uuid}`）。
3. 如果新增参数，同步更新：
   - `FileUploadRequest` 字段；
   - `to_api_params()` 的映射；
   - `TestDataLoader._load()` 的 `valid_fields`；
   - `AnalysisEndpoints.analysis_upload_file()` 的 `param_mapping`。
4. 运行后通过 `ids=get_case_display_name` 在 pytest/Allure 中看到中文用例名。

---

## 10. 现状问题清单（仅记录，未修改）

> 以下按「影响主链路 / 影响可运行性 / 维护成本」排序。行号基于当前文件内容。

### 10.1 会导致用例无法运行或结果失真

| # | 位置 | 问题 | 影响 |
| --- | --- | --- | --- |
| 1 | `api/tests/conftest.py:41` 与 `:231` | 同名 `pytest_configure` 定义两次，后者覆盖前者 | `--env/--api-timeout/--api-auto-login` 不生效；`TestDataLoader.load()` 不执行；`allure.dynamic.environment` 不写入 |
| 2 | `api/endpoints/analysis_endpoints.py:175` | `analysis_upload_filepath` 的 `**kwargs` 分支引用未定义的 `mapping` | 传任意可选参数即 `NameError` |
| 3 | `api/endpoints/analysis_endpoints.py:133-139` vs `api/tests/test_analysis.py:325-335` | endpoint 形参是 `file_path/file_name/file_type`，测试传的是 `filepath/filename/filetype` | 该用例直接 `TypeError` |
| 4 | `ui/tests/ui_base_test.py` | 只有 `UIBaseTest`，没有 `BaseDesignTest`；但 `test_measure.py`、`test_canvs.py`、`test_workflow.py`、`test_performance.py`、`test_coverage.py` 都继承 `BaseDesignTest` | 5 个测试文件 collection 失败 |
| 5 | `ui/tests/test_model_viewer.py`、`test_annotation.py`、`test_design.py` | 使用了未定义的 fixture `model_viewer`、`uploaded_model`、`fresh_uploaded_model`；`DesignPage` 未导入/未定义 | 用例无法执行 |
| 6 | `common/base_test.py:168-225` | 代理了 `BaseAssertion` 不存在的方法（`assert_greater_equal`、`assert_less_equal`、`assert_not_contains`、`assert_empty`、`assert_not_empty`、`has_soft_assert_failures`、`soft_assert_in`、`soft_assert_greater`、`soft_assert_less`） | 调用即 `AttributeError` |
| 7 | `ui/tests/ui_base_test.py:292-298` | 代理 `UIAssertion` 不存在的 `soft_assert_element_visible` / `soft_assert_element_text` | 调用即 `AttributeError` |
| 8 | `ui/tests/test_measure.py`、`test_performance.py`、`test_workflow.py` | 使用了 `AttachmentType`，但文件只 `import allure` 并从 `ui_base_test` 导入基类（未导入该符号；对比 `test_canvs.py`、`test_coverage.py` 是正确导入的） | `NameError` |
| 9 | `ui/tests/test_view_operations.py:85` | `with self.step.log_step(...)`，`log_step` 返回 `None` | `AttributeError: __enter__` |
| 10 | `ui/methods/iframe_methods.py:26` | `self._get_locator('viewer_3d', 'canvas')`，`BaseMethods` 无此方法（只有 `base_page.get_locator`） | 运行到即 `AttributeError` |
| 11 | `api/tests/test_analysis.py:21` 起 | 测试类未继承 `APIBaseTest`，`self.assertion`/`self.api_assert` 不存在；只能依赖原生 `assert` | 断言层设计未被主链路使用 |
| 12 | `api/core/api_base_test.py:33` | 把 `self.assertion` 换成 `APIAssertion`，但 `api_context` 类属性从未赋值 | `_on_assert_fail_screenshot` 永远拿不到请求/响应 |

### 10.2 配置/入口问题

| # | 位置 | 问题 |
| --- | --- | --- |
| 13 | `pytest.ini:10` | `testpaths = tests`，但项目根目录没有 `tests/`（实际是 `api/tests`、`ui/tests`）；直接运行 `pytest` 会找不到路径 |
| 14 | `pytest.ini:6` | `disable_test_id_escaping_and_forfeit_functions_to_configure` 不是 pytest 合法 ini 项（合法项是 `disable_test_id_escaping_and_forfeit_all_rights_to_community_support`） |
| 15 | `pytest.ini` + 两个 `conftest.py` | `--env` 在两个 conftest 中重复注册；marker 注册分散（`smoke`/`slow` 重复） |
| 16 | `run_tests.py:34` | `pytest tests/` 指向不存在的目录 |
| 17 | `run_case.py:11` | 指向不存在的 `test_cases.py` |
| 18 | `test_case.py:7` | `from test_methods import ...`，模块不存在；且使用 async Playwright + `pytest.mark.asyncio`（未注册 marker、未装 pytest-asyncio） |
| 19 | `run_tests_with_allure.py` | 先按平台判断命令，随后又无条件执行 Windows 的 `cmd /c allure ...`；`start_report_server()` 里 `chdir("ui/allure-report")` 但报告生成目录是根目录 `allure-report` |
| 20 | `requirements.txt` | UTF-16 编码；缺少 `thefuzz`（faker_handle 依赖）、`jsonschema`（可选断言）、`pytest-asyncio`（遗留 async 用例）等 |
| 21 | `ui/tests/conftest.py:11` | `browser_context_args` 依赖 pytest-playwright，但依赖未安装且基类自行管理浏览器 |

### 10.3 结构与维护成本

| # | 位置 | 问题 |
| --- | --- | --- |
| 22 | `api/core/base_api.py` | 名为 base API，实际是 `WebhookListener` 的早期副本，与 `common/utils/webhook_utils/webhook_listener.py` 同名不同实现 |
| 23 | `api/core/base_methods.py` | 空文件 |
| 24 | `common/utils/data_utils/data_loader.py:61` | 默认数据路径指向 `model_test/api/data/test.yaml`（不存在），且与 `api/data/analysis_test_data.py::TestDataLoader` 重名 |
| 25 | `api/data/analysis_test_data.json`、`api/data/enevts.yaml` | 无引用 |
| 26 | `common/utils/data_utils/add_data.py:1-2` | 顶层导入 `data_utils.glob_data`、`tools.logger`，在本项目结构下不可导入 |
| 27 | `common/utils/webhook_utils/webhook_server.py:5` | `from models.webhook_record import Session, WebhookRecordModel`，项目中无 `models/`；该 Flask 服务不能独立启动 |
| 28 | `common/utils/webhook_utils/webhook_listener.py:31` | docstring 写「从 Redis 读取」，实现是 HTTP 轮询 + SQLite |
| 29 | `ui/context/ui_context.py:29-36` | 只挂载 `base/view/measure/toolbar`，未挂载 `iframe/annotation/canvas/model_info`；但历史用例调用 `self.design.iframe_methods`、`self.design.canvas`、`self.design.annotation` |
| 30 | `ui/methods/*` | 选择器大量硬编码，与 `ui/locators/*.yaml` 两套并存 |
| 31 | `ui/locators/viewer_locators.yaml` | 空文件 |
| 32 | `api/tests/test_analysis.py` | 6 个参数化方法主体完全重复，仅分组不同 |
| 33 | `common/utils/logger.py` | 每条日志默认 `allure.attach`，报告体积会随日志量线性膨胀 |
| 34 | `APIContext._attach_to_allure` | 直接输出原始 headers，包含 `Authorization`；`APIAllureHelper._sanitize_headers` 的脱敏没有被使用 |
| 35 | `AuthManager._fetch_new_token` | 明文打印 access_token |
| 36 | `settings.py:60-61, 108-113` | `APP_SECRET`、邮箱授权码、webhook key 硬编码 |
| 37 | `venv/`、`.idea/`、`allure-results/`、`ui/screenshots/`、`common/logs/` | 运行产物/本地环境进入工作树，未见 `.gitignore` |
| 38 | 多个文件头 | 路径注释与实际文件不符（复制粘贴痕迹），影响检索 |
| 39 | `ui/tests/test_design.py` | 未 `import DesignPage`，且 `TestViewOperations` 与另一文件重名 |
| 40 | `api/core/base_api.py:99`、各测试文件 `__main__` | 调试代码、清空报告、`os.system` 生成报告等逻辑直接写在库/用例文件里 |

---

## 11. 建议的整理顺序（文档层面，不涉及本次改动）

1. **先保主链路**：修 `api/tests/conftest.py` 的重复 `pytest_configure`、`analysis_upload_filepath` 的参数名/`mapping`，让 API 主用例可稳定执行。
2. **再统一断言入口**：补齐 `BaseAssertion` 缺失方法，或删掉 `BaseTest` 中不存在的代理，避免运行期 `AttributeError`。
3. **清理 UI 历史文件**：把 `BaseDesignTest` 相关用例归入归档目录，或补齐基类与 fixture；保留 `test_view_operations.py` + `UIBaseTest` 作为当前 UI 主链路。
4. **收敛重复实现**：`TestDataLoader`、`WebhookListener`、配置加载器各保留一套；删除 `api/core/base_api.py`、空 `base_methods.py`、无引用 JSON/YAML。
5. **统一配置与入口**：`pytest.ini` 的 `testpaths` 改为实际目录（或删除），入口脚本只保留一套，删掉 Windows-only 命令。
6. **安全与报告体积**：脱敏 headers/token，关闭日志默认 attach 或降级为 debug。
7. **补 `.gitignore`**：`venv/`、`.idea/`、`allure-results/`、`allure-report/`、`__pycache__/`、`*.log`、`webhook_data.db` 等。

---

> 再次说明：本文档仅梳理现状，未修改任何代码文件。
