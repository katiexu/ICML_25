import torch
import numpy as np
import pennylane as qml
from pennylane import CircuitGraph
from pennylane import numpy as pnp
from torch.nn import functional as F
import random

from Arguments import Arguments
args = Arguments()

dev = qml.device("default.qubit", wires=args.n_qubits)

# app=1: Fidelity Task; app=2: MAXCUT; app=3: VQE
@qml.qnode(dev)
def circuit_qnode(circuit_list, app=1, hamiltonian=None, edge=None):
    for params in list(circuit_list):
        if params == 'START':
            continue
        elif params[0] == 'Rot':
            theta = pnp.array(params[2], requires_grad=True)
            phi = pnp.array(params[3], requires_grad=True)
            delta = pnp.array(params[4], requires_grad=True)
            qml.Rot(theta, phi, delta, wires=params[1])
        elif params[0] == 'PauliX':
            qml.PauliX(wires=params[1])
        elif params[0] == 'PauliY':
            qml.PauliY(wires=params[1])
        elif params[0] == 'PauliZ':
            qml.PauliZ(wires=params[1])
        elif params[0] == 'Hadamard':
            qml.Hadamard(wires=params[1])
        elif params[0] == 'RX':
            param = pnp.array(params[2], requires_grad=True)
            qml.RX(param, wires=params[1])
        elif params[0] == 'RY':
            param = pnp.array(params[2], requires_grad=True)
            qml.RY(param, wires=params[1])
        elif params[0] == 'RZ':
            param = pnp.array(params[2], requires_grad=True)
            qml.RZ(param, wires=params[1])
        elif params[0] == 'CNOT':
            qml.CNOT(wires=[params[1], params[2]])
        elif params[0] == 'CZ':
            qml.CZ(wires=[params[1], params[2]])
        elif params[0] == 'U3':
            theta = pnp.array(params[2], requires_grad=True)
            phi = pnp.array(params[3], requires_grad=True)
            delta = pnp.array(params[4], requires_grad=True)
            qml.U3(theta, phi, delta, wires=params[1])
        elif params[0] == 'C(U3)':
            theta = pnp.array(params[3], requires_grad=True)
            phi = pnp.array(params[4], requires_grad=True)
            delta = pnp.array(params[5], requires_grad=True)
            qml.ctrl(qml.U3, control=params[1])(theta, phi, delta, wires=params[2])
        elif params[0] == 'SWAP':
            qml.SWAP(wires=[params[1], params[2]])
        elif params == 'END':
            break
        else:
            print(params)
            raise ValueError("There exists operations not in the allowed operation pool!")

    if app == 1:
        return qml.state()
    elif app == 2:
        if edge is None:
            return qml.sample()
        if hamiltonian != None:
            return qml.expval(hamiltonian)
        else:
            raise ValueError("Please pass a hamiltonian as an observation for QAOA_MAXCUT!")
    elif app == 3:
        if hamiltonian != None:
            return qml.expval(hamiltonian)
        else:
            raise ValueError("Please pass a hamiltonian as an observation for VQE!")
    else:
        print("Note: Currently, there are no correspoding appllications!")


def GVAE_translator(data_uploading, rot, enta):

    single_list = []
    enta_list = []

    for i in range(0, args.n_layers):
        single_item = []
        for j in range(0, args.n_qubits):
            d = int(data_uploading[j][i])
            r = int(rot[j][i])
            combination = f'{d}{r}'
            if combination == '00':
                theta = np.random.uniform(0, 2 * np.pi)
                phi = np.random.uniform(0, 2 * np.pi)
                delta = np.random.uniform(0, 2 * np.pi)
                single_item.append(('Rot', j, theta, phi, delta))
            elif combination == '01':
                angle = np.random.uniform(0, 2 * np.pi)
                single_item.append(('RX', j, angle))
            elif combination == '10':
                angle = np.random.uniform(0, 2 * np.pi)
                single_item.append(('RY', j, angle))
            elif combination == '11':
                angle = np.random.uniform(0, 2 * np.pi)
                single_item.append(('RZ', j, angle))
        single_list.append(single_item)

        enta_item = []
        for k in range(0, args.n_qubits):
            et = int(enta[k][i])
            if k == et - 1:
                theta = np.random.uniform(0, 2 * np.pi)
                phi = np.random.uniform(0, 2 * np.pi)
                delta = np.random.uniform(0, 2 * np.pi)
                enta_item.append(('Rot', k, theta, phi, delta))
            else:
                theta = np.random.uniform(0, 2 * np.pi)
                phi = np.random.uniform(0, 2 * np.pi)
                delta = np.random.uniform(0, 2 * np.pi)
                enta_item.append(('C(U3)', k, et - 1, theta, phi, delta))
        enta_list.append(enta_item)

    circuit_ops = []
    for layer in range(0, args.n_layers):
        circuit_ops.extend(single_list[layer])
        circuit_ops.extend(enta_list[layer])

    return circuit_ops

def generate_circuits(net):
    data_uploading = []
    rot = []
    enta = []

    for i in range(0, len(net), 3):
        data_uploading.append(net[i])
        rot.append(net[i + 1])
        enta.append(net[i + 2])

    circuit_ops = GVAE_translator(data_uploading, rot, enta)

    return circuit_ops

# transform a circuit into a circuit graph
def get_circuit_graph(circuit_list):
    circuit_qnode(circuit_list)
    tape = circuit_qnode.qtape
    ops = tape.operations
    obs = tape.observables
    return CircuitGraph(ops, obs, tape.wires)

# encode allowed gates in one-hot encoding
def encode_gate_type():
    gate_dict = {}
    ops = args.allowed_gates.copy()
    ops.insert(0, 'START')
    ops.append('END')
    ops_len = len(ops)
    ops_index = torch.tensor(range(ops_len))
    type_onehot = F.one_hot(ops_index, num_classes=ops_len)
    for i in range(ops_len):
        gate_dict[ops[i]] = type_onehot[i]
    return gate_dict

# get the gate and adjacent matrix of a circuit
def get_gate_and_adj_matrix(circuit_list):
    gate_matrix = []
    op_list = []
    cl = list(circuit_list).copy()
    if cl[0] != 'START':
        cl.insert(0, 'START')
    if cl[-1] != 'END':
        cl.append('END')
    cg = get_circuit_graph(circuit_list)
    gate_dict = encode_gate_type()
    gate_matrix.append(gate_dict['START'].tolist() + [1] * args.n_qubits)
    op_list.append('START')
    for op in cg.operations:
        op_list.append(op)
        op_qubits = [0] * args.n_qubits
        for i in op.wires:
            op_qubits[i] = 1
        op_vector = gate_dict[op.name].tolist() + op_qubits
        gate_matrix.append(op_vector)
    gate_matrix.append(gate_dict['END'].tolist() + [1] * args.n_qubits)
    op_list.append('END')

    op_len = len(op_list)
    adj_matrix = np.zeros((op_len, op_len), dtype=int)
    for op in cg.operations:
        ancestors = cg.ancestors_in_order([op])
        descendants = cg.descendants_in_order([op])
        if len(ancestors) == 0:
            adj_matrix[0][op_list.index(op)] = 1
        else:
            if op.name in ['CNOT', 'CZ', 'SWAP', 'C(U3)']:
                count = 0
                wires = set()
                for ancestor in ancestors[::-1]:
                    wires.update(set(ancestor.wires) & set(op.wires))
                    if not len(wires) == count:
                        adj_matrix[op_list.index(ancestor)][op_list.index(op)] = 1
                        count += 1
                    if count == 2:
                        break
                if count == 1:
                    adj_matrix[0][op_list.index(op)] = 1
            else:
                direct_ancestor = ancestors[-1]
                adj_matrix[op_list.index(direct_ancestor)][op_list.index(op)] = 1
        if op.name in ['CNOT', 'CZ', 'SWAP', 'C(U3)']:
            wires = set()
            for descendant in descendants:
                wires.update(set(descendant.wires) & set(op.wires))
                if isinstance(descendant, qml.measurements.StateMP):
                    adj_matrix[op_list.index(op)][op_len - 1] = 1
                if len(wires) == 2:
                    break
        else:
            if isinstance(descendants[0], qml.measurements.StateMP):
                adj_matrix[op_list.index(op)][op_len - 1] = 1

    return cl, gate_matrix, adj_matrix