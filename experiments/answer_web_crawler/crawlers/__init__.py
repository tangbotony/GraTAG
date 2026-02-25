from .perplexity import PerplexityCrawler
from .tiangong import TiangongCrawler
from .ernie import ErnieCrawler
from .kimi import KimiCrawler
from .metaso import MetasoCrawler
from .chatglm import ChatGLMCrawler
from .baichuan import BaichuanCrawler
from .tongyi import TongyiCrawler

CRAWLER_MAP = {
    "perplexity": PerplexityCrawler,
    "tiangong": TiangongCrawler,
    "ernie": ErnieCrawler,
    "kimi": KimiCrawler,
    "metaso": MetasoCrawler,
    "chatglm": ChatGLMCrawler,
    "baichuan": BaichuanCrawler,
    "tongyi": TongyiCrawler,
}
