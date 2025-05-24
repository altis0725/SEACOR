import os
import yaml
import json

def load_yaml(path):
    """
    YAMLファイルを読み込んでdictとして返す
    """
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)

def load_agents(agent_dir):
    """
    agentsディレクトリ配下の全YAMLを読み込んで1つのdictにまとめる
    """
    agents = {}
    for filename in os.listdir(agent_dir):
        if filename.endswith(".yaml"):
            data = load_yaml(os.path.join(agent_dir, filename))
            # MetaAgent: {...} の場合はflatten
            if "MetaAgent" in data:
                agents.update(data["MetaAgent"])
            else:
                agents.update(data)
    return agents

def load_tasks(task_dir):
    """
    tasksディレクトリ配下の全YAMLを読み込んで1つのdictにまとめる
    """
    tasks = {}
    for filename in os.listdir(task_dir):
        if filename.endswith(".yaml"):
            data = load_yaml(os.path.join(task_dir, filename))
            # MetaTask: {...} の場合はflatten
            if "MetaTask" in data:
                tasks.update(data["MetaTask"])
            else:
                tasks.update(data)
    return tasks

def load_crews(crew_dir):
    """
    crewsディレクトリ配下の全YAMLを読み込んで1つのdictにまとめる
    """
    crews = {}
    for filename in os.listdir(crew_dir):
        if filename.endswith(".yaml"):
            data = load_yaml(os.path.join(crew_dir, filename))
            # MetaCrew: {...} の場合はflatten
            if "MetaCrew" in data:
                crew_data = data["MetaCrew"]
            else:
                crew_data = data
            crew_name = crew_data.get("name", os.path.splitext(filename)[0])
            crews[crew_name] = crew_data
    return crews

def load_tools(tools_path):
    """
    tools.yamlを読み込んでdictとして返す
    """
    return load_yaml(tools_path)

def reencode_json_to_utf8(path):
    """
    meta_crew.jsonなどをensure_ascii=Falseで再保存し、日本語を可読化するワークアラウンド関数
    """
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
