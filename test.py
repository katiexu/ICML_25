import matplotlib.pyplot as plt
import networkx as nx
from qiskit import QuantumCircuit
from qiskit.converters import circuit_to_dag

# 创建一个示例量子电路
qc = QuantumCircuit(2)
qc.h(0)
qc.cx(0, 1)
qc.measure_all()

# 将量子电路转换为 DAG
dag = circuit_to_dag(qc)

# 使用 NetworkX 创建图
graph = nx.DiGraph()

# 添加节点和边
for node in dag.topological_op_nodes():
    graph.add_node(node._node_id, label=node.name)
    for child in dag.successors(node):
        graph.add_edge(node._node_id, child._node_id)

# 获取节点标签
labels = nx.get_node_attributes(graph, 'label')

# 绘制图
plt.figure(figsize=(12, 8))
nx.draw(graph, with_labels=True, labels=labels, node_size=3000, node_color='lightblue', font_size=10, font_weight='bold', arrows=True, arrowstyle='->', arrowsize=15)
plt.title('Quantum Circuit DAG')
plt.show()