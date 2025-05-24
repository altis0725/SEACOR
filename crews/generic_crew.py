import os
import json
from crewai import Agent, Task, Crew, Process
from utils.yaml_loader import load_agents, load_tasks, load_crews, load_tools, reencode_json_to_utf8
from tools.monica_llm import MonicaLLM
from core.custom_task import CustomTask

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AGENT_DIR = os.path.join(BASE_DIR, "config", "agents")
TASK_DIR = os.path.join(BASE_DIR, "config", "tasks")
CREW_DIR = os.path.join(BASE_DIR, "config", "crews")
TOOLS_PATH = os.path.join(BASE_DIR, "config", "tools.yaml")

agents_yaml = load_agents(AGENT_DIR)
tasks_yaml = load_tasks(TASK_DIR)
crews_yaml = load_crews(CREW_DIR)
tools_yaml = load_tools(TOOLS_PATH)

monica_conf = tools_yaml["monica_llm"]
monica_llm = MonicaLLM(
    api_key=os.environ.get(monica_conf.get("api_key_env", "MONICA_API_KEY")),
    endpoint=monica_conf.get("endpoint"),
    model=monica_conf.get("model"),
    temperature=monica_conf.get("temperature", 0.7),
    max_tokens=monica_conf.get("max_tokens", 2000)
)

def pre_task_description_hook(crew_name, task_id, prompt=None, main_task_output=None, system_message=None):
    desc = tasks_yaml[task_id]["description"]
    # 利用可能なActionリストをtools.yamlのキー名で自動埋め込み
    action_names = list(tools_yaml.keys())
    action_list_str = "\n- " + "\n- ".join(action_names)
    action_example = f"Action: {action_names[0]}\nAction Input: {{\"query\": \"ユーザーからの入力\", \"system_message\": \"システムメッセージ\"}}"
    action_instruction = f"""
【利用可能なAction（ツール）一覧】
{action_list_str}

ツールを使う場合は、必ず以下の形式で出力してください。

Action: {{Action名}}
Action Input: {{ ... }}  # ツールに渡す入力（JSON形式）

例：
{action_example}

Action名は必ず上記リストのいずれかから選んでください。
説明文やテンプレート文は出力しないでください。
最終回答を出す場合は「Final Answer: ...」の形式で出力してください。
"""
    desc = action_instruction + "\n" + desc
    if prompt:
        desc += f"\n\n【ユーザー入力】\n{prompt}"
    if main_task_output is not None:
        desc += f"\n\n【main_taskの出力】\n{main_task_output}"
    if system_message:
        desc += f"\n\n【system_message】\n{system_message}"
    if task_id == "evolution_task":
        desc += f"\n\n【現状のagent定義】\n{json.dumps(agents_yaml, ensure_ascii=False, indent=2)}"
    if task_id == "flow_review_task":
        desc += f"\n\n【現状のcrew構成】\n{json.dumps(crews_yaml, ensure_ascii=False, indent=2)}"
    return desc

class BaseCrewBuilder:
    def build_agent(self, agent_id, no_tools=False):
        conf = agents_yaml[agent_id]
        return Agent(
            name=conf["name"],
            role=conf["role"],
            goal=conf["goal"],
            backstory=conf.get("backstory", ""),
            tools=[] if no_tools else ([monica_llm] if "monica_llm" in conf.get("tools", []) else []),
            allow_delegation=conf.get("allow_delegation", False),
            verbose=conf.get("verbose", False),
            llm=monica_llm
        )

    def build_task(self, task_id, prompt=None, main_task_output=None, system_message=None, crew_name=None):
        desc = pre_task_description_hook(crew_name, task_id, prompt, main_task_output, system_message)
        conf = tasks_yaml[task_id]
        return CustomTask(
            description=desc,
            agent=self.build_agent(conf["agent"]),
            expected_output=conf.get("expected_output", ""),
            human_input=conf.get("human_input", False)
        )

    def build_crew(self, crew_name, prompt=None, system_message=None):
        conf = crews_yaml[crew_name]
        manager_agent_id = conf["manager_agent"]
        manager_agent = self.build_agent(manager_agent_id, no_tools=True)
        agent_objs = [self.build_agent(aid) for aid in conf["agents"] if aid != manager_agent_id]
        task_objs = [self.build_task(tid, prompt, system_message=system_message, crew_name=crew_name) for tid in conf["tasks"]]
        process = (
            Process.hierarchical if conf.get("process") == "hierarchical"
            else Process.sequential
        )
        if manager_agent is None and agent_objs:
            manager_agent = agent_objs[0]
        return Crew(
            agents=agent_objs,
            tasks=task_objs,
            process=process,
            manager_agent=manager_agent,
            verbose=conf.get("verbose", False),
            output_log_file=conf.get("output_log_file"),
            memory_config=conf.get("memory")
        )

class MainCrewBuilder(BaseCrewBuilder):
    def build_crew(self, crew_name, prompt=None, system_message=None):
        conf = crews_yaml[crew_name]
        manager_agent_id = conf["manager_agent"]
        manager_agent = self.build_agent(manager_agent_id, no_tools=True)
        agent_objs = [self.build_agent(aid) for aid in conf["agents"] if aid != manager_agent_id]
        main_task = self.build_task("main_task", prompt, system_message=system_message, crew_name=crew_name)
        main_task_output = main_task.run()
        task_objs = [main_task]
        for tid in conf["tasks"]:
            if tid == "main_task":
                continue
            task_objs.append(self.build_task(tid, prompt, main_task_output=main_task_output, system_message=system_message, crew_name=crew_name))
        process = (
            Process.hierarchical if conf.get("process") == "hierarchical"
            else Process.sequential
        )
        if manager_agent is None and agent_objs:
            manager_agent = agent_objs[0]
        return Crew(
            agents=agent_objs,
            tasks=task_objs,
            process=process,
            manager_agent=manager_agent,
            verbose=conf.get("verbose", False),
            output_log_file=conf.get("output_log_file"),
            memory_config=conf.get("memory")
        )

def get_crew_builder(crew_name):
    if crew_name == "main_crew":
        return MainCrewBuilder()
    else:
        return BaseCrewBuilder()

# --- フック関数群（クルーごとに特殊処理を追加したい場合ここに記述） ---
def pre_kickoff_hook(crew_name, prompt, system_message):
    # クルーごとに前処理を分岐
    if crew_name == "main_crew":
        pass
    elif crew_name == "evolution_crew":
        pass
    return prompt, system_message

def post_kickoff_hook(crew_name, result):
    if crew_name == "main_crew":
        pass
    elif crew_name == "evolution_crew":
        pass
    return result

async def kickoff_async_crew(crew_name, prompt, system_message=""):
    prompt, system_message = pre_kickoff_hook(crew_name, prompt, system_message)
    builder = get_crew_builder(crew_name)
    crew = builder.build_crew(crew_name, prompt, system_message=system_message)
    result = await crew.kickoff_async(inputs={"prompt": prompt, "system_message": system_message})
    result = post_kickoff_hook(crew_name, result)
    return result 