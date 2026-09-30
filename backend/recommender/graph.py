"""Career-skill knowledge graph built from the processed dataset.

Nodes are careers (`career:<O*NET-SOC code>`) and skills. A skill node is an
O*NET rated element (`onet:<element id>`), an O*NET tool (`tool:<name>`) or
an ESCO skill (`esco:<id>`); an ESCO skill that the mapping step merged into
an O*NET skill uses that O*NET node instead of its own. Each edge says a
career requires a skill, weighted 0-1:

- O*NET rated skills: importance, kept only when rated at least Important
- O*NET tools: 1.0 In Demand, 0.75 Hot Technology, 0.5 other
- ESCO skills: consensus weight over the linked ESCO occupations

When two sources give the same career-skill edge, the higher weight wins and
both sources are recorded.
"""

from collections import deque
from functools import lru_cache

import networkx as nx
import pandas as pd

from pipeline import PROCESSED_DIR

# Importance 3 ("Important") on O*NET's 1-5 scale. Every career is rated on
# all 68 elements, so without a cutoff every career links to every generic
# skill; at this cutoff each career keeps 15-33 of them.
IMPORTANCE_CUTOFF = 0.5


def career_id(onet_soc_code):
    return f'career:{onet_soc_code}'


def esco_id(skill_uri):
    return f"esco:{skill_uri.rsplit('/', 1)[1]}"


def onet_node_id(source, skill_id):
    return f'onet:{skill_id}' if source == 'onet_skill' else f'tool:{skill_id}'


def read(name):
    return pd.read_csv(PROCESSED_DIR / name, dtype={'onet_soc_code': str}, keep_default_na=False, na_values=[''])


def esco_node_ids():
    """ESCO skill URI -> graph node id, resolving merges into O*NET nodes."""
    mapping = read('esco_onet_map.csv')
    return {
        uri: onet_node_id(source, skill_id) if merged else esco_id(uri)
        for uri, source, skill_id, merged in zip(
            mapping['skill_uri'], mapping['onet_source'], mapping['onet_skill_id'], mapping['merged'],
        )
    }


def build_graph():
    graph = nx.Graph()

    for row in read('occupations.csv').itertuples():
        graph.add_node(career_id(row.onet_soc_code), kind='career', label=row.title, domain=row.domain,
                       description=row.description)

    def require(career, skill, weight, source, label, skill_type):
        if skill not in graph:
            graph.add_node(skill, kind='skill', label=label, skill_type=skill_type)
        if graph.has_edge(career, skill):
            edge = graph.edges[career, skill]
            edge['weight'] = max(edge['weight'], weight)
            edge['sources'].add(source)
        else:
            graph.add_edge(career, skill, weight=weight, sources={source})

    rated = read('onet_skills.csv')
    for row in rated[rated['importance'] >= IMPORTANCE_CUTOFF].itertuples():
        require(career_id(row.onet_soc_code), onet_node_id('onet_skill', row.element_id),
                row.importance, 'onet_skill', row.skill, row.skill_type)

    for row in read('onet_tools.csv').itertuples():
        require(career_id(row.onet_soc_code), onet_node_id('onet_tool', row.tool),
                row.weight, 'onet_tool', row.tool, 'tool')

    node_ids = esco_node_ids()
    esco = read('esco_occupation_skills.csv').merge(read('esco_skills.csv').fillna({'skill_type': ''}), on='skill_uri')
    for row in esco.itertuples():
        require(career_id(row.onet_soc_code), node_ids[row.skill_uri],
                row.weight, 'esco', row.label, row.skill_type)

    return graph


class KnowledgeGraphManager:
    """Read-only access to the knowledge graph. Build it once with `load()`."""

    def __init__(self, graph):
        self.graph = graph

    @classmethod
    def load(cls):
        return cls(build_graph())

    def node(self, node_id):
        return self.graph.nodes[node_id]

    def careers(self):
        return [n for n, kind in self.graph.nodes(data='kind') if kind == 'career']

    def skills(self):
        return [n for n, kind in self.graph.nodes(data='kind') if kind == 'skill']

    def skills_of(self, career):
        """{skill node: edge weight} for everything the career requires."""
        return {skill: data['weight'] for _, skill, data in self.graph.edges(career, data=True)}

    def careers_requiring(self, skill):
        return {career: data['weight'] for _, career, data in self.graph.edges(skill, data=True)}

    def traverse(self, start_nodes, max_depth):
        """Breadth-first search from `start_nodes`, stopping after `max_depth` hops.

        Returns {node: hops from the nearest start node}. From skill nodes,
        careers requiring them are 1 hop away, skills those careers require
        are 2, and careers sharing those skills are 3.
        """
        depth = {node: 0 for node in start_nodes if node in self.graph}
        queue = deque(depth)
        while queue:
            node = queue.popleft()
            if depth[node] == max_depth:
                continue
            for neighbour in self.graph.neighbors(node):
                if neighbour not in depth:
                    depth[neighbour] = depth[node] + 1
                    queue.append(neighbour)
        return depth


@lru_cache(maxsize=1)
def get_graph():
    """The shared graph, built on first use and reused for the process lifetime."""
    return KnowledgeGraphManager.load()
