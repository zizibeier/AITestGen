# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概览

pytest + Allure 自动化测试工程，包含两条测试线：

| 测试线 | 位置 | 被测对象 | 运行依赖 |
| --- | --- | --- | --- |
| API | `api/tests/` | Forface 3D 解析/报价接口（`https://api.forface3d.com`） | 外网、有效 AppID/Secret、webhook 回调服务 |
| UI | `ui/tests/` | JLC 3D Viewer 前端（`https://3d-viewer.jlc.com/`） | Playwright Chromium、`files/` 下的模型文件 |

Python 3.13。请使用 `venv/bin/python`：仓库里还有 `.venv`、`.venv-1`，依赖安装不完整。

## 脚本生成规范（必须遵守）
- 生成 API 用例：必须使用 `APIContext` 和 `Endpoints` 工厂，不要直接 import `requests`。数据驱动必须把 case 加到 `api/data/analysis_test_data.yaml` 中。
- 生成 UI 用例：必须继承 `UIBaseTest`，用 `self.context.methods.xxx` 调用业务动作，禁止直接写 `page.locator`。
- 断言：必须使用 `self.assert_xxx`（硬断言）或 `self.soft_assert_xxx`（软断言），禁止直接写 `assert`。注意，已知问题 5 中缺失的方法**不要生成**。
- 生成后的校验：必须执行 `.venv/bin/python -m pytest <文件> --collect-only`，确保语法和 fixture 没问题。


## AI 日志分析指引
当用例失败时，请按以下顺序排查：
1. 测试日志：`common/logs/` 下的最新 `.log` 文件。
2. Allure 附件：如果有 `allure-results/`，失败用例的请求/响应报文和截图会在里面。
3. UI 截图：`ui/screenshots/` 下的截图，用于判断是 3D 渲染问题还是元素加载问题。
请读取上述日志，结合 `rework.md` 里的已知问题，输出 JSON 格式的根因分析。

## 绝对红线（违规直接重写）
1. **禁止手动传 Token**：底层 `APIContext` 和 `AuthManager` 已经自动处理了 `Authorization` 鉴权。在编写测试用例和 `endpoints` 时，**绝对不要**手动去调用登录接口，也**不要**手动往 headers 里塞 Token。
2. **禁止直接使用 requests**：所有网络请求必须通过 `APIContext.request()` 发起，以复用重试和 Allure 附件功能。
3. **直接调用业务封装**：如果在 `api/endpoints/` 下已经封装了对应的方法（如 `analysis_upload_file`），测试用例中必须直接调用该方法，无需关心入参拼接。
## 常用命令


## 接口文档规范
- 所有外部导入的 OpenAPI/Swagger 接口文档，统一存放在 `docs/api_specs/` 目录下。
- 当用户要求“生成某个接口的测试脚本”时，请先使用 `Glob` 工具扫描该目录，找到对应的 JSON/YAML 文件并读取。
- 严禁在 `docs/api_specs/` 目录之外散落接口文档。


所有命令都在仓库根目录执行。

```bash
# 环境（仅首次）
venv/bin/pip install -r requirements.txt   # requirements.txt 是 UTF-16 编码；pip 解析失败时先转成 UTF-8
venv/bin/playwright install chromium       # UI 测试前置

# API 测试
venv/bin/python -m pytest api/tests -v
venv/bin/python -m pytest api/tests -m smoke
venv/bin/python -m pytest api/tests -k webhook -v
venv/bin/python -m pytest "api/tests/test_analysis.py::TestAnalysisEndpoints::test_upload_with_webhook_wait" -v

# UI 测试
venv/bin/python -m pytest ui/tests/test_view_operations.py -v
venv/bin/python -m pytest "ui/tests/test_view_operations.py::TestViewOperations::test_rotate_view" -v

# AI 断言的离线用例（在线用例在未配置 AI_ASSERT_API_KEY / CEREBRAS_API_KEY 时自动跳过）
venv/bin/python -m pytest api/tests/test_ai_assertion.py -q

# Allure 报告（pytest.ini 已默认 --alluredir=allure-results）
allure generate allure-results -o allure-report --clean
```

注意：

- 不要在根目录直接运行 `pytest`：`pytest.ini` 的 `testpaths = tests` 指向不存在的目录，请显式传测试目录。
- 不要在同一次 pytest 调用里同时收集 `api/tests` 和 `ui/tests`：两个 `conftest.py` 都注册了 `--env`，会报 `ValueError: option names {'--env'} already added`。
- `allure` 命令行工具未随依赖安装；没有它时测试仍会写 `allure-results/`，只是无法生成 HTML 报告。
- UI 是否无头由 `common/config/settings.py` 的 `Config.HEADLESS` 决定。`ui/tests/conftest.py` 的 `--headed` 只服务于 pytest-playwright 的 `browser_context_args`，不会改变 `UIBaseTest` 的行为。

### 测试前置条件

- **API**：`AuthManager` 用 `Config.APP_ID` / `Config.APP_SECRET` 自动换取 token；webhook 用例还要求 `Config.WEBHOOK_BASE_URL` 可访问。以上凭据从仓库根目录的 `.env` 读取（模板见 `.env.example`，`.env` 不入库）；未配置时相关在线用例自动跳过。
- **UI**：`Config.AUTO_UPLOAD_MODEL = True`，`UIBaseTest.setup_class()` 会自动上传 `files/气垫.STEP` 并等待 Canvas 就绪；`Config.AUTO_LOGIN = False`。

## 目录职责

```
api/          API 测试线
  core/       APIContext（Session/重试/请求历史/Allure 附件）、AuthManager、APIBaseTest
  endpoints/  业务接口封装，一个领域一个 *_endpoints.py；路径来自 api/data/api_config.yaml
  assertions/ APIAssertion：HTTP 状态码、JSON path、业务 code
  data/       analysis_test_data.yaml（用例数据）+ 加载器 + api_config.yaml（接口路径）
  tests/      conftest.py（session fixture / marker / 失败钩子）+ test_*.py

ui/           UI 测试线
  context/    UIContext：导航、登录、上传模型、等待加载、iframe、业务方法挂载点
  pages/      BasePage：加载定位器 YAML、元素原子操作、高亮与失败调试
  methods/    按能力域拆分的业务动作：view / measure / toolbar / iframe / annotation / canvas ...
  locators/   选择器 YAML（main_page / iframe / locators / viewer）
  assertions/ UIAssertion：元素、页面、Canvas/WebGL
  tests/      ui_base_test.py（UIBaseTest，管理 Playwright 生命周期）+ test_*.py

common/       两条测试线共用的公共层
  base_test.py           BaseTest：用例生命周期、断言代理、日志、性能、重试
  config/settings.py     Config / TestConfig / CIConfig / EmailConfig
  context/base_context.py BaseContext 抽象：setup/teardown/get_session/navigate/wait_for
  assertions/            BaseAssertion（硬/软断言）+ AIAssertion（LLM 判定）
  utils/                 logger（控制台+文件+Allure）、allure_helper、performance_monitor、
                         data_utils（DataHandle 占位符引擎）、webhook_utils、email_sender
  decorator/             endpoint / wait / webhook 装饰器（目前主链路未使用）

files/        测试模型（stp/step/obj/dxf/dwg/stl/3mf）
rework.md     现有工程的详细架构与问题梳理，改代码前值得先读
```

产物目录：`allure-results/`、`allure-report/`、`common/logs/`、`ui/screenshots/`。

## 架构

### 分层与调用链

依赖方向是 `tests → 业务层 → 上下文层 → 基础层`，`common` 不反向依赖 `api` / `ui`。

**API：**

```
test_*.py
  └─ fixture endpoints(api)                 # api/tests/conftest.py
       └─ AnalysisEndpoints(ctx)            # api/endpoints/
            └─ APIContext.request(...)      # api/core/api_context.py
                 ├─ requests.Session + Retry
                 ├─ AuthManager.get_auth_header()   # 自动加 Bearer，跳过 Config.TOKEN_URL
                 ├─ allure.attach 请求/响应
                 └─ 记录 _last_request / _last_response
  └─ WebhookListener(Config.WEBHOOK_BASE_URL).wait_for_event(...)
```

**UI：**

```
test_*.py
  └─ UIBaseTest.setup_class()               # ui/tests/ui_base_test.py
       ├─ sync_playwright → chromium → BrowserContext → Page
       └─ UIContext(page)
            ├─ BasePage(page) + main_page_locators.yaml
            ├─ BaseMethods / ViewMethods / MeasurementMethods / ToolbarMethods
            └─ navigate() → upload_model() → wait_for_model_load() → switch_to_iframe()
  └─ setup_method() → UIAssertion(page, screenshot_callback)
```

### 断言

`BaseTest` 把断言委托给断言器：`self.assert_*`（硬断言）、`self.soft_assert_*` + `self.assert_all()`（软断言）、`self.assert_ai(...)`（LLM 语义断言）。`APIBaseTest` 换成 `APIAssertion`，`UIBaseTest` 换成 `UIAssertion`。测试用例应使用这些代理方法，而不是直接写原生 `assert`。

### 数据驱动

**现有示例**：`api/data/analysis_test_data.yaml` 是 Analysis 接口的数据源。其流转链路为：
YAML groups/cases -> `TestDataLoader` -> `DataHandle.process_data()` 替换占位符 -> `FileUploadRequest` -> `@pytest.mark.parametrize` 驱动用例。

**通用占位符**：支持 `${global:key}`、`${getfile:目录:stp}`、`${uuid}`、`${datetime_now}`、`${random_int(1,10)}`、`${faker:...}` 等。


**⚠️ 新增接口的数据源规范（极其重要）**：
1. **禁止将所有数据塞进同一个 YAML**。每个业务域必须有独立的 YAML 数据文件（如 `api/data/user_test_data.yaml`、`api/data/order_test_data.yaml`）。
2. 每个 YAML 文件必须有对应的 Python Loader 类（参考 `analysis_test_data.py`），负责将 YAML 数据转换成对应接口的 Request 数据类（如 `UserLoginRequest`）。
3. 如果新接口的数据结构简单，可以直接在测试用例里用 `@pytest.mark.parametrize` 写内联数据；但**只要涉及文件上传、复杂依赖或超过 5 条用例，必须走 YAML 数据驱动**。
4. 生成新数据文件后，必须同步更新对应测试用例中的 `parametrize` 引用。

### 配置

优先级（实际）：pytest 命令行参数 → 环境变量（`API_APP_ID`/`API_APP_SECRET`、`UI_USERNAME`/`UI_PASSWORD`、`API_AUTO_LOGIN`、`WEBHOOK_*`、`AI_ASSERT_*`、`EMAIL_*`）→ `.env`（`common/config/settings.py` 用 `load_dotenv(override=False)` 加载）→ `Config` 默认值。凭据一律写 `.env`，不要写回代码。
接口路径在 `api/data/api_config.yaml`，UI 选择器在 `ui/locators/*.yaml`。

## 代码约定

- 测试用例只做「流程编排 + 断言」，不在用例里直接写 `requests` 或 `page.locator`。
- **新增 API 领域**：在 `api/data/api_config.yaml` 加路径 → 新建 `api/endpoints/<domain>_endpoints.py` → 在 `api/endpoints/__init__.py` 导出 → 在 `api/tests/conftest.py` 的 `Endpoints` 工厂加属性 → 写 `test_*.py`。
- **新增 UI 能力**：在 `ui/methods/` 新建继承 `BaseMethods` 的类（一个能力域一个文件）→ 在 `UIContext.__init__` 挂载 → 用例继承 `UIBaseTest`。
- **新增数据驱动用例**：在 YAML 对应分组追加 case，字段用 snake_case；新增参数时同步修改 `FileUploadRequest` 字段、`to_api_params()` 映射、`TestDataLoader._load()` 的合法字段和 `AnalysisEndpoints.analysis_upload_file()` 的 `param_mapping`。
- 金额相关逻辑统一用 `Decimal`，不要用 `float`。
- Allure：分组用 `@allure.epic/feature/story`，动态标题/描述用 `allure.dynamic`，步骤用 `allure.step` 或 `self.log_info()`。

## 已知问题（读代码/排错时会踩到）

1. `api/tests/conftest.py` 里 `pytest_configure` 定义了两次，后者覆盖前者：`--env` / `--api-timeout` / `--api-auto-login` 不会写回 `Config`，`TestDataLoader.load()` 和 `allure.dynamic.environment` 也不会执行。
2. `ui/tests/` 中 `test_canvs.py`、`test_measure.py`、`test_performance.py`、`test_workflow.py`、`test_coverage.py` 从 `ui_base_test` 导入不存在的 `BaseDesignTest`，收集即报错；`test_model_viewer.py`、`test_annotation.py`、`test_design.py` 使用未定义的 `model_viewer` / `uploaded_model` / `fresh_uploaded_model` fixture。目前可运行的是 `test_view_operations.py`。
3. `api/core/base_api.py` 名不副实，内容是一份 `WebhookListener` 副本，不是 API 基类。
4. `api/endpoints/analysis_endpoints.py` 的 `analysis_upload_filepath()` 在传可选参数时引用了未定义的 `mapping`；同文件 `test_analysis.py::test_analysis_upload_file` 传的是 `filepath/filename/filetype`，与形参 `file_path/file_name/file_type` 不匹配。
5. `common/base_test.py` 代理了 `BaseAssertion` 中不存在的若干方法（`assert_greater_equal`、`assert_less_equal`、`assert_not_contains`、`assert_empty`、`assert_not_empty`、`soft_assert_in/greater/less`、`has_soft_assert_failures`），调用即 `AttributeError`；`UIBaseTest` 的 `soft_assert_element_visible/text` 同理。
6. 根目录 `run_case.py`、`run_tests.py`、`run_tests_with_allure.py` 指向了不存在的路径或写死 Windows 命令，优先直接用 `pytest`。
7. `common/utils/data_utils/data_loader.py` 是另一套同名 `TestDataLoader`（默认读不存在的 `model_test/api/data/test.yaml`），API 线实际使用的是 `api/data/analysis_test_data.py`。
