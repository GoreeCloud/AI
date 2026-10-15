"""Installed Ollama model catalog must not infer availability."""
import unittest
from dataclasses import dataclass
from reference.ollama_model_catalog import OllamaModelCatalog, CatalogError

@dataclass(frozen=True)
class Model:
    name: str
    size_bytes: int | None

class Fake:
    def __init__(self, values=()): self.values=values
    def list_models(self): return self.values

class CatalogTests(unittest.TestCase):
    def test_qwen_gemma_only_when_installed(self):
        catalog=OllamaModelCatalog(Fake((Model("qwen3:8b",123), Model("gemma3:4b",456))))
        self.assertEqual([m.family for m in catalog.installed()],["Gemma","Qwen"])
        self.assertFalse(any(m.tools_verified for m in catalog.installed()))
        with self.assertRaises(CatalogError):
            catalog.select("llama3:latest")

    def test_unavailable_and_invalid_names(self):
        catalog=OllamaModelCatalog(Fake())
        self.assertEqual(catalog.installed(),())
        with self.assertRaises(CatalogError):
            catalog.select("gemma3:4b")
        with self.assertRaises(CatalogError):
            catalog.select("https://external.invalid")

if __name__=="__main__":
    unittest.main()
