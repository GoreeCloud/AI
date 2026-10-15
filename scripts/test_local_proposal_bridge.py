"""Synthetic Ollama response to capability preview."""
import json
import unittest
from reference.integration_directory import example_directory
from reference.capability_requirements import RequirementCatalog, OperationRequirement
from reference.local_action_planner import propose_with_local_ollama
from reference.local_model_gateway import ChatResult, LocalOllamaGateway

class FakeGateway(LocalOllamaGateway):
    def chat(self, model, messages, *, max_tokens=None):
        return ChatResult('ollama', model, 'local', self.reply)

class BridgeTests(unittest.TestCase):
    def test_draft_only(self):
        runtime = FakeGateway()
        runtime.reply = json.dumps(dict(schema='goreecloud.ai.action-proposal.v1', service='github', operation='repos.read', resource='repo:sample/test', arguments={'page':1}))
        directory = example_directory()
        directory.bind('github', connection_id='demo', transport='mcp')
        requirements = RequirementCatalog()
        requirements.register(OperationRequirement('github','repos.read','read',('mcp',),'v1'))
        plan = propose_with_local_ollama(runtime,'sample:latest','List repositories',request_id='req-1',directory=directory,requirements=requirements,permitted_services=frozenset({'github'}),permitted_operations=frozenset({'github:repos.read'}))
        self.assertEqual(plan.redacted_preview()['status'],'proposed_not_authorized')

if __name__ == '__main__':
    unittest.main()
