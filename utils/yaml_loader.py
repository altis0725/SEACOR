import yaml
import json
import os
import glob

def load_yaml(path):
    """
    YAMLファイルまたはディレクトリを読み込んでdictとして返す。
    ディレクトリの場合は配下の*.yaml/*.ymlをすべてマージする。
    """
    if os.path.isdir(path):
        result = {}
        for file in sorted(glob.glob(os.path.join(path, "*.yaml")) + glob.glob(os.path.join(path, "*.yml"))):
            with open(file, encoding="utf-8") as f:
                data = yaml.safe_load(f)
                if data:
                    result.update(data)
        return result
    else:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)

def reencode_json_to_utf8(json_path):
    """JSONファイルをUTF-8で再エンコードするユーティリティ"""
    try:
        with open(json_path, encoding="utf-8") as f:
        data = json.load(f)
        with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"reencode_json_to_utf8 error: {e}")
