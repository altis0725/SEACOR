import os
import json
import logging
import traceback
from crewai import Agent, Task, Crew, LLM
from utils.yaml_loader import load_yaml
from tools.monica_llm import MonicaLLM
# crewai_tools系ツールをimport
from crewai_tools import BraveSearchTool, ScrapeWebsiteTool, SpiderTool

# ログ設定（ファイルにも出力）
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/app/logs/generic_crew_debug.log', encoding='utf-8')
    ]
)

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
AGENT_DIR = os.path.join(BASE_DIR, "config", "agents")
TASK_DIR = os.path.join(BASE_DIR, "config", "tasks")
CREW_DIR = os.path.join(BASE_DIR, "config", "crews")
TOOLS_PATH = os.path.abspath(os.path.join(BASE_DIR, "config", "tools.yaml"))

agents_yaml = load_yaml(AGENT_DIR)
tasks_yaml = load_yaml(TASK_DIR)
crews_yaml = load_yaml(CREW_DIR)
tools_yaml = load_yaml(TOOLS_PATH)

print("[DEBUG] agents_yaml:", json.dumps(agents_yaml, ensure_ascii=False, indent=2))
print("[DEBUG] tasks_yaml:", json.dumps(tasks_yaml, ensure_ascii=False, indent=2))
print("[DEBUG] crews_yaml:", json.dumps(crews_yaml, ensure_ascii=False, indent=2))
print("[DEBUG] tools_yaml:", json.dumps(tools_yaml, ensure_ascii=False, indent=2))

#monica_llm = MonicaLLM();
monica_llm = LLM(
    model="gpt-4o-mini",
    api_key=os.environ.get("MONICA_API_KEY"),
    base_url="https://openapi.monica.im/v1"
)

class DynamicCrewBuilder:
    """動的に設定を読み込むCrewビルダー"""
    
    def __init__(self, crew_name: str, prompt: str = None, system_message: str = None):
        self.crew_name = crew_name
        self.prompt = prompt
        self.system_message = system_message
        try:
            self.crew_config = crews_yaml[crew_name].copy()
        except Exception as e:
            print(f"[ERROR] crew_name={crew_name} の取得に失敗: {e}")
            traceback.print_exc()
            raise
        print(f"[DEBUG] crew_config: {json.dumps(self.crew_config, ensure_ascii=False, indent=2)}")
    
    def process_config(self, conf):
        """configの型チェックと変換"""
        if "config" not in conf or not isinstance(conf["config"], dict):
            conf["config"] = {}
        elif isinstance(conf["config"], str):
            try:
                conf["config"] = json.loads(conf["config"])
                if not isinstance(conf["config"], dict):
                    conf["config"] = {}
            except Exception:
                conf["config"] = {}
        return conf

    def build_agent(self, agent_id: str, no_tools: bool = False) -> Agent:
        """動的にエージェントを構築"""
        try:
            conf = agents_yaml[agent_id].copy()
        except Exception as e:
            print(f"[ERROR] agent_id={agent_id} の取得に失敗: {e}")
            traceback.print_exc()
            raise
        if no_tools:
            conf["tools"] = []
        elif "tools" in conf:
            tool_objs = []
            for t in conf["tools"]:
                if isinstance(t, str):
                    if t in tools_yaml:
                        tool_conf = tools_yaml[t]
                        if tool_conf.get("provider") == "crewai_tools":
                            class_name = tool_conf.get("class")
                            if class_name == "BraveSearchTool":
                                tool_objs.append(BraveSearchTool())
                            elif class_name == "ScrapeWebsiteTool":
                                tool_objs.append(ScrapeWebsiteTool())
                            elif class_name == "SpiderTool":
                                tool_objs.append(SpiderTool())
                            else:
                                logging.warning(f"未対応のcrewai_tools: {class_name}")
                        else:
                            logging.warning(f"未対応のprovider: {tool_conf.get('provider')}")
                    else:
                        logging.warning(f"tools_yamlに未定義: {t}")
                else:
                    tool_objs.append(t)
            conf["tools"] = tool_objs
        # llmが未指定またはmonica_llmの場合はインスタンスをセット
        if not conf.get("llm") or conf.get("llm") == "monica_llm":
            conf["llm"] = monica_llm
        conf.setdefault("backstory", "")
        #conf = self.process_config(conf)
        return Agent(**conf)

    def build_task(self, task_id: str, prompt: str = None, 
                  main_task_output: str = None, system_message: str = None) -> Task:
        """動的にタスクを構築"""
        try:
            conf = tasks_yaml[task_id].copy()
        except Exception as e:
            print(f"[ERROR] task_id={task_id} の取得に失敗: {e}")
            traceback.print_exc()
            raise
        conf = self.process_config(conf)
        # output_pydanticのクラス変換
        if "output_pydantic" in conf and isinstance(conf["output_pydantic"], str):
            if conf["output_pydantic"] == "utils.evolution_models.EvolutionOutput":
                try:
                    from utils.evolution_models import EvolutionOutput
                    conf["output_pydantic"] = EvolutionOutput
                except Exception as e:
                    print(f"[ERROR] output_pydanticクラスimport失敗: {e}")
                    conf["output_pydantic"] = None
        return Task(**conf)

    def build_crew(self) -> Crew:
        """動的にクルーを構築"""
        print(f"[DEBUG] build_crew crew_config: {json.dumps(self.crew_config, ensure_ascii=False, indent=2)}")
        agent_ids = self.crew_config.get("agents")
        task_ids = self.crew_config.get("tasks")
        if not agent_ids or not task_ids:
            raise ValueError(f"crew_configに'agents'または'tasks'キーがありません: {self.crew_config}")
        print(f"[DEBUG] build_crew agent_ids: {agent_ids}")
        print(f"[DEBUG] build_crew task_ids: {task_ids}")
        # 直接crew_configに代入
        self.crew_config["agents"] = [self.build_agent(aid) for aid in agent_ids]
        self.crew_config["tasks"] = [self.build_task(tid, self.prompt, system_message=self.system_message) for tid in task_ids]
        # マネージャーエージェントの処理
        if "manager_agent" in self.crew_config:
            self.crew_config["manager_agent"] = self.build_agent(
                self.crew_config["manager_agent"], 
                no_tools=True
            )
        print(f"[DEBUG] build_crew agents: {self.crew_config['agents']}")
        print(f"[DEBUG] build_crew tasks: {self.crew_config['tasks']}")

        if self.crew_config.get("planning_llm") == "monica_llm":
            self.crew_config["planning_llm"] = monica_llm
        if self.crew_config.get("manager_llm") == "monica_llm":
            self.crew_config["manager_llm"] = monica_llm
        if self.crew_config.get("function_calling_llm") == "monica_llm":
            self.crew_config["function_calling_llm"] = monica_llm

        try:
            return Crew(**self.crew_config)
        except Exception as e:
            print("[ERROR] Crew生成時例外:", e)
            traceback.print_exc()
            raise

async def kickoff_async_crew(crew_name: str, prompt: str, system_message: str = ""):
    """非同期でクルーを実行"""
    try:
        builder = DynamicCrewBuilder(crew_name, prompt, system_message)
        crew = builder.build_crew()
        result = await crew.kickoff_async(inputs={"prompt": prompt, "system_message": system_message})
        return result
    except Exception as e:
        print(f"[ERROR] kickoff_async_crew例外: {e}")
        traceback.print_exc()
        raise 