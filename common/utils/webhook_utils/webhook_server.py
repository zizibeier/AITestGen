# webhook_server.py
from flask import Flask, request, Response
import json
import logging
from datetime import datetime
from models.webhook_record import Session, WebhookRecordModel

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)


def extract_event_id(data: dict) -> str:
    """提取事件 ID"""
    payload = data.get('payload', {})
    service_info = payload.get('serviceInfo', {})
    return service_info.get('event', '')


def extract_file_id(data: dict) -> str:
    """提取文件 ID"""
    payload = data.get('payload', {})
    data_obj = payload.get('data', {})
    return data_obj.get('id', '')


def extract_file_name(data: dict) -> str:
    """提取文件名"""
    payload = data.get('payload', {})
    data_obj = payload.get('data', {})
    return data_obj.get('fileName', '')


def normalize_payload(payload: dict) -> dict:
    """
    标准化 payload，移除动态字段
    只保留结构体，忽略时间戳、签名等动态值
    """
    # 需要忽略的动态字段
    ignore_fields = ['timestamp', 'nonce', 'signature', 'createTime', 'updateTime']

    def clean(obj):
        if isinstance(obj, dict):
            return {
                k: clean(v) for k, v in obj.items()
                if k not in ignore_fields and not k.endswith('Time') and not k.endswith('Timestamp')
            }
        elif isinstance(obj, list):
            return [clean(item) for item in obj]
        else:
            return obj

    return clean(payload)


@app.route('/webhook', methods=['POST'])
def webhook():
    """接收 Webhook 回调"""
    try:
        raw_data = request.get_data(as_text=True)
        json_data = request.get_json()

        if not json_data:
            return Response('OK', status=200)

        event_id = extract_event_id(json_data)
        file_id = extract_file_id(json_data)
        file_name = extract_file_name(json_data)
        payload = json_data.get('payload', {})

        # 存储原始 payload（不做标准化，保留原始数据）
        session = Session()
        record = WebhookRecordModel(
            event_id=event_id,
            file_id=file_id,
            file_name=file_name,
            payload_json=json.dumps(payload, ensure_ascii=False)
        )
        session.add(record)
        session.commit()
        session.close()

        logging.info(f"已存储: event={event_id}, file={file_name}")

        return Response('OK', status=200)

    except Exception as e:
        logging.error(f"处理失败: {e}")
        return Response('OK', status=200)


@app.route('/compare/<event_id>', methods=['GET'])
def compare_by_event(event_id: str):
    """
    按事件索引比对结构体
    获取该事件最近两次的 payload，比对结构
    """
    session = Session()

    # 获取该事件的最新两条记录
    records = session.query(WebhookRecordModel).filter(
        WebhookRecordModel.event_id == event_id
    ).order_by(WebhookRecordModel.created_at.desc()).limit(2).all()

    session.close()

    if len(records) < 2:
        return {
            'event_id': event_id,
            'message': '不足两次记录，无法比对',
            'records_count': len(records)
        }

    # 标准化 payload（移除动态字段）
    latest_payload = normalize_payload(json.loads(records[0].payload_json))
    previous_payload = normalize_payload(json.loads(records[1].payload_json))

    # 比对结构
    diff = compare_structure(previous_payload, latest_payload)

    return {
        'event_id': event_id,
        'latest': {
            'time': records[0].created_at.isoformat(),
            'file_name': records[0].file_name,
            'file_id': records[0].file_id
        },
        'previous': {
            'time': records[1].created_at.isoformat(),
            'file_name': records[1].file_name,
            'file_id': records[1].file_id
        },
        'is_same': len(diff) == 0,
        'differences': diff
    }


def compare_structure(obj1, obj2, path=""):
    """递归比对两个 JSON 结构"""
    differences = []

    if type(obj1) != type(obj2):
        differences.append({
            'path': path or 'root',
            'type_diff': f'{type(obj1).__name__} vs {type(obj2).__name__}'
        })
        return differences

    if isinstance(obj1, dict):
        all_keys = set(obj1.keys()) | set(obj2.keys())
        for key in all_keys:
            new_path = f"{path}.{key}" if path else key
            if key not in obj1:
                differences.append({'path': new_path, 'added': True})
            elif key not in obj2:
                differences.append({'path': new_path, 'removed': True})
            else:
                differences.extend(compare_structure(obj1[key], obj2[key], new_path))

    elif isinstance(obj1, list):
        if len(obj1) != len(obj2):
            differences.append({
                'path': path or 'root',
                'list_length_diff': f'{len(obj1)} vs {len(obj2)}'
            })
        else:
            for i, (item1, item2) in enumerate(zip(obj1, obj2)):
                differences.extend(compare_structure(item1, item2, f"{path}[{i}]"))

    return differences


@app.route('/history', methods=['GET'])
def history():
    """查看历史记录"""
    session = Session()
    records = session.query(WebhookRecordModel).order_by(
        WebhookRecordModel.created_at.desc()
    ).limit(50).all()
    session.close()

    return {
        'total': len(records),
        'records': [r.to_dict() for r in records]
    }


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)