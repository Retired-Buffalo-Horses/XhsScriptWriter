"""
写稿服务

"""

import os
from datetime import datetime
import sys
from string import Template
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

import dotenv

from autogen import (
    AfterWorkOption,
    ConversableAgent,
    SwarmResult,
    initiate_swarm_chat,
    LLMConfig,
)
from pydantic import BaseModel


class Script(BaseModel):
    title: str
    content: str


class WriteScriptService:
    # pylint: disable=too-many-instance-attributes

    def __setup_logger(self, level: str, logger_name: str, log_folder_path: Path) -> logging.Logger:
        try:
            log_file_size_mb = float(os.getenv("LOG_FILE_SIZE_MB", "1"))
        except ValueError as e:
            # 如果LOG_FILE_SIZE_MB不能转换为float,使用默认值1MB
            print(f"警告: LOG_FILE_SIZE_MB 设置无效,使用默认值1MB. 错误: {e}")
            log_file_size_mb = 1.0

        # 确保日志目录存在
        log_folder_path.mkdir(parents=True, exist_ok=True)

        root = logging.getLogger(logger_name)

        # 根据环境变量设置日志级别
        root.setLevel(getattr(logging, level.upper()))

        formatter = logging.Formatter(fmt="%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

        file_handler = RotatingFileHandler(
            filename=log_folder_path.joinpath("editorial.log"),
            maxBytes=1024 * 1024 * log_file_size_mb,
            backupCount=3,
        )
        # 文件处理器使用相同的日志级别
        file_handler.setLevel(getattr(logging, level.upper()))
        file_handler.setFormatter(formatter)

        console_handler = logging.StreamHandler()
        # 控制台处理器使用相同的日志级别
        console_handler.setLevel(getattr(logging, level.upper()))
        console_handler.setFormatter(formatter)

        root.addHandler(file_handler)
        root.addHandler(console_handler)

        return root

    def __load_config(self, config_path: str, model_tag: str = "STD") -> LLMConfig:
        """
        从配置文件加载LLM配置列表

        Args:
            config_path: 配置文件路径
            model_tag: 模型标签，默认为"STD"
        Returns:
            List[Dict[str, Any]]: 配置字典列表
        """

        filter_dict = {"tags": [model_tag]}

        return LLMConfig.from_json(path=config_path).where(**filter_dict)

    def __init__(self):
        dotenv.load_dotenv()
        self.log_folder_path = Path(os.getenv("LOG_FOLDER_PATH", "log"))
        self.logging = self.__setup_logger(os.getenv("LOG_LEVEL", "INFO"), __name__, self.log_folder_path)

        self.llm_config_path = os.getenv("LLM_CONFIG_PATH", "config/llm_config.json")
        self.llm_config = self.__load_config(self.llm_config_path)
        self.llm_config_mini = self.__load_config(self.llm_config_path, "MINI")

        # 设定本服务需要的模型的温度
        self.llm_config._model.temperature = 0.5
        self.llm_config_mini._model.temperature = 0.3

        # 预定义所有agent
        self.write_direction_agent = None
        self.write_script_agent = None
        self.review_script_agent = None

    def __init_agents(self, script_length: int, prompt_file: str):
        # 需要时使用，深度debug数据
        # logging_session_id = autogen.runtime_logging.start(logger_type="file", config={"filename": "runtime.log"})
        # print("Logging session ID: " + str(logging_session_id))

        script_sample_file_path = "script_sample.txt"
        if not Path(script_sample_file_path).exists():
            self.logging.error(f"{script_sample_file_path} 没找到，无法继续工作")
            raise FileNotFoundError(f"{script_sample_file_path} not found")

        with open(script_sample_file_path, "r", encoding="utf-8") as f:
            script_sample_text = f.read()

        # 检查是否有自定义的提示词文件路径
        write_script_agent_prompt_file_path = prompt_file

        self.logging.info(f"使用提示词文件：{write_script_agent_prompt_file_path}")

        if not os.path.exists(write_script_agent_prompt_file_path):
            err_msg = f"没有找到提示词文件，无法继续运行 ： {write_script_agent_prompt_file_path}"
            self.logging.error(err_msg)
            raise FileNotFoundError(err_msg)

        with open(write_script_agent_prompt_file_path, "r", encoding="utf-8") as f:
            write_script_agent_prompt = f.read()

        script_length = (script_length if script_length else 250)

        self.logging.info(f"指定script_length：{script_length}")

        # 使用string.Template处理prompt
        template = Template(write_script_agent_prompt)
        write_script_agent_prompt = template.safe_substitute(script_length=script_length)

        def finish_write_script(title: str, content: str, context_variables: dict) -> SwarmResult:
            """
            Tool for Write_Script_Agent to finish its work and pass data to the next agent.

            Args:
                title: str
                content: str
                context_variables: dict

            Returns:
                SwarmResult
            """
            context_variables["title"] = title
            context_variables["content"] = content
            return SwarmResult(agent=self.review_script_agent, context_variables=context_variables)

        output_safety_prompt_file_path = "script_prompts/output_safty.prompt"
        if not os.path.exists(output_safety_prompt_file_path):
            err_msg = f"没有找到提示词文件，无法继续运行 ： {output_safety_prompt_file_path}"
            self.logging.error(err_msg)
            raise FileNotFoundError(err_msg)

        with open(output_safety_prompt_file_path, "r", encoding="utf-8") as f:
            output_safety_prompt = f.read()

        system_message = f"""
你是专业的小红书自媒体号的编辑，你的工作是根据输入的写作方向，生成一篇新的用于小红书的文章.
文章长度为{script_length}字，请确保文章长度符合要求。

请按照以下要求撰写脚本：
{write_script_agent_prompt}

{output_safety_prompt}

以下是一些较为优秀的作品的Sample，供你模仿，请你模仿Sample的写作手法遣词造句，并且如果某些商品在Sample中出现过，请直接使用Sample中的描述：
{script_sample_text}

---

请通过调用工具finish_write_script将你撰写的脚本（content）和标题（title）传递给下一个Agent。

注意：
 - 不要使用任何形式的"```json"或"```"定界符。
 - 请确认文章长度符合要求"""

        self.logging.info(f"write_script_agent提示词：{system_message}")

        # 写手Agent
        self.write_script_agent = ConversableAgent(
            name="Write_Script_Agent",
            llm_config=self.llm_config,
            description="Agent for writing a news script",
            system_message=system_message,
            functions=[finish_write_script],
        )

        def finish_review_script(title: str, content: str, context_variables: dict) -> SwarmResult:
            """
            Tool for Review_Script_Agent to finish its work and pass data to the next agent.

            Args:
                title: str
                content: str
                context_variables: dict

            Returns:
                SwarmResult
            """
            context_variables["title"] = title
            context_variables["content"] = content
            return SwarmResult(agent=AfterWorkOption.TERMINATE, context_variables=context_variables)

        # 审核Agent
        self.review_script_agent = ConversableAgent(
            name="Review_Script_Agent",
            llm_config=self.llm_config_mini,
            description="Agent for reviewing and refining a news script",
            system_message=f"""
你是专业的小红书自媒体号的编辑，你的工作是审核和修正context_variables中的脚本（content）：
1. 检查并修正行文不畅的地方，确保符合简体中文的语法和用语习惯，没有语病（但为了适应小红书生态而使用网络用语是必要的或特殊用词是被鼓励的）
2. 检查脚本长度，如果大幅超过{script_length}字，请尽可能缩减到{script_length}字以内，同时保留核心内容和风格
3. 保持原有的小红书文章的风格和语气，不要改变内容的本质！

请注意：
- 请仅按照context_variables["content"]和context_variables["title"]工作
- 你的任务是优化而非重写，除非需要缩减字数
- 修改后的内容应保持原有的吸引力和小红书特色

请通过调用工具finish_review_script将修改后的脚本（content）和标题（title）传递给下一个Agent。
不要使用任何形式的"```json"或"```"定界符。""",
            functions=[finish_review_script],
        )

    def write_script(self, writing_direction: str, script_length: int = 250, prompt_file: str = "script_prompts/write_script_agent.prompt") -> Script:
        task = f"本次工作的写作方向：{writing_direction}"

        task += "\n请基于以上写作方向，撰写一篇适用于小红书的文稿；不需要提供任何思考过程或额外说明"

        self.logging.debug(f"撰写脚本的task: {task[:100]}")

        try:
            self.__init_agents(script_length, prompt_file)
        except Exception as e:
            self.logging.error(f"初始化agents失败: {e}")
            return None

        std_output_file = f"ag2_std_write_script_{datetime.now().strftime('%Y%m%d%H%M%S')}.txt"
        std_output_file_path = self.log_folder_path.joinpath(std_output_file)
        sys.stdout = open(std_output_file_path, "w", encoding="utf-8")
        try:
            context_variables = {
                "outline": None,
                "title": None,
                "content": None,
            }

            self.logging.info("启动写作")
            chat_result, context_variables, _ = initiate_swarm_chat(
                initial_agent=self.write_script_agent,
                agents=[
                    self.write_script_agent,
                    self.review_script_agent,
                ],
                messages=task,
                context_variables=context_variables,
                max_rounds=6,
            )

            self.logging.debug(f"ag2的输出：{chat_result}")

            try:
                title = context_variables["title"]
                content = context_variables["content"]
            except Exception as e:
                self.logging.error(f"解析ag2的输出失败，输出结果可能造成后续无法继续工作，但仍然继续输出：{e}")

            self.logging.info(f"完成写作：{title}")

            return Script(title=title, content=content)

        except Exception as e:
            err_msg = f"ag2执行任务失败: {e}"
            self.logging.error(err_msg)
            return None
        finally:
            sys.stdout.close()
            sys.stdout = sys.__stdout__

if __name__ == "__main__":
    write_script_service = WriteScriptService()
    script = write_script_service.write_script("哈氏咸圈，最完美的下午茶伴侣")
    print(script)
