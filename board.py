from qiskit import QuantumCircuit, ClassicalRegister, QuantumRegister, transpile
from qiskit_aer import AerSimulator
from termcolor import colored


class Board:
    def __init__(self, size=3):
        # Initialize the quantum circuit with one qubit and classical bit for each cell
        self.size = size
        self.entanglement_count = 0
        self.cells = [[' ' for _ in range(size)] for _ in range(size)] # Initialize the board representation
        
        self.simulator = AerSimulator()
        self.qubits = QuantumRegister(size**2, 'q')
        self.bits = ClassicalRegister(size**2, 'c')
        
        self.circuit = QuantumCircuit(self.qubits, self.bits)
        self.circuit.reset(self.qubits) 
        self.circuit.barrier()
        
        ''' For a 3x3 board, the winning lines are:
        - Horizontal lines: (0, 1, 2), (3, 4, 5), (6, 7, 8)
        - Vertical lines: (0, 3, 6), (1, 4, 7), (2, 5, 8)
        - Diagonal lines: (0, 4, 8), (2, 4, 6)
        '''
        self.winning_lines = [tuple(range(i, size**2, size)) for i in range(size)] + \
                             [tuple(range(i * size, (i + 1) * size)) for i in range(size)] + \
                             [tuple(range(0, size**2, size + 1)), tuple(range(size - 1, size**2 - 1, size - 1))]
                              

    def __str__(self):
        # Create a colorful string representation of the board
        board_str = ''
        for i, row in enumerate(self.cells):
            for cell in row:
                if '?' in cell: cell_color = 'cyan' # Quantum move
                elif cell == 'X': cell_color = 'red'
                elif cell == 'O': cell_color = 'green'
                else: cell_color = 'yellow'
                board_str += f' {colored(cell, cell_color)} '
                board_str += '|' if '?' in cell else ' |'
                
            board_str = board_str[:-1] + '\n' # Remove last separator
            if i < self.size - 1: # Add horizontal separator
                board_str += '-' * (5 * self.size - 1) + '\n'
        return board_str

    
    def make_classical_move(self, row, col, player_mark):
        if self.cells[row][col] == ' ': # Check if the cell is occupied
            self.cells[row][col] = player_mark
            index = row * self.size + col
            
            if player_mark == 'X': self.circuit.x(self.qubits[index])
            else: self.circuit.id(self.qubits[index])
            return True
        return False


    def make_swap_move(self, row1, col1, row2, col2):
        # Swap the quantum states of 2 cells
        if self.cells[row1][col1] != ' ' and self.cells[row2][col2] != ' ':
            indices = [row1 * self.size + col1, row2 * self.size + col2]
            self.circuit.swap(self.qubits[indices[0]], self.qubits[indices[1]])
            self.cells[row1][col1], self.cells[row2][col2] = self.cells[row2][col2], self.cells[row1][col1]
            return True
        return False
    

    def make_entangled_move(self, *positions, player_mark):
        # Apply quantum moves, including pairwise and triple entanglements
        if len(positions) not in [2, 3]: return False
        if any(self.cells[row][col] != ' ' for row, col in positions): return False
        if len(set(positions)) != len(positions): return False
        
        indices = [row * self.size + col for row, col in positions]
        if len(positions) == 2: # Standard Pairwise Entanglement using CNOT gate
            self.circuit.h(self.qubits[indices[0]])
            self.circuit.cx(self.qubits[indices[0]], self.qubits[indices[1]])
        else: # Triple Entanglement using Toffoli gate
            self.circuit.h(self.qubits[indices[0]]) # Apply Hadamard gate to the first qubit
            self.circuit.cx(self.qubits[indices[0]], self.qubits[indices[1]]) # Apply CNOT gate between the first and second qubits
            self.circuit.ccx(self.qubits[indices[0]], self.qubits[indices[1]], self.qubits[indices[2]]) # Apply Toffoli gate
        
        for row, col in positions: self.cells[row][col] = player_mark + '?'
        self.entanglement_count += 1
        return True
    
    
    def can_be_collapsed(self):
        # Determine if a measurement should be made based on complex conditions.
        # Condition: measure if the entanglements reach 3 or more,
        # And if entangled cells form a potential winning line => measure
        if self.entanglement_count >= 3:
            for line in self.winning_lines:
                if all(self.cells[i // self.size][i % self.size].endswith('?') for i in line): 
                    return True
        return False
    

    def collapse_board(self):
        # Simulate the measurement process and update the board accordingly
        self.circuit.barrier()
        self.circuit.measure(self.qubits, self.bits) # Measure the quantum state to collapse it to classical states
        
        transpiled_circuit = transpile(self.circuit, self.simulator)
        job = self.simulator.run(transpiled_circuit, memory=True)
        counts = job.result().get_counts()
        max_state = max(counts, key=counts.get)[::-1] # Get the state with the highest probability
        
        # Update the board based on the measurement results and apply the corresponding classical moves
        for i in range(self.size ** 2):
            row, col = divmod(i, self.size)
            if self.cells[row][col].endswith('?'):
                self.cells[row][col] = 'X' if max_state[i] == '1' else 'O'
        self.entanglement_count = 0
        return counts

    
    def check_win(self):
        # Dynamic implementation for above logic with dynamic winning lines
        for line in self.winning_lines:
            # Check if all cells in the line are the same and not empty
            first_cell = self.cells[line[0] // self.size][line[0] % self.size]
            is_same = all(self.cells[i // self.size][i % self.size] == first_cell for i in line)
            if is_same and first_cell not in [' ', 'X?', 'O?']: return first_cell
                
        # If no spaces and no entanglements left => 'Draw'
        # If all cells are filled but there are entanglements => collapse_board
        if all(self.cells[i // self.size][i % self.size] not in [' '] for i in range(self.size**2)):
            if self.entanglement_count <= 0: return 'Draw'
            return self.entanglement_count
        return None