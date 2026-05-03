import asyncio
from app.config import get_settings
from app.db.neo4j_client import Neo4jClient
from app.core.graph_rag import GraphRAGService
from openai import AsyncOpenAI

async def main():
    s = get_settings()
    neo = Neo4jClient(s.NEO4J_URI, s.NEO4J_USER, s.NEO4J_PASSWORD)
    svc = GraphRAGService(AsyncOpenAI(api_key=s.OPENAI_API_KEY), neo)
    q = 'CYP2C9 and VKORC1 warfarin dosing in CKD'
    rule = svc.extract_entities_rule_based(q)
    print('RULE', rule)
    ctx = await svc.traverse_graph(rule, depth=2)
    print('NODES', len(ctx.nodes))
    print('EDGES', len(ctx.edges))
    print('ENTITIES_FOUND', ctx.entities_found)
    print('FIRST_NODES', [n.label for n in ctx.nodes[:10]])
    print('FIRST_EDGES', [f"{e.source}-{e.relationship}-{e.target}" for e in ctx.edges[:10]])
    await neo.close()

asyncio.run(main())
