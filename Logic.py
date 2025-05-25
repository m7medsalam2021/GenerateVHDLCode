import tkinter as tk
from tkinter import ttk 
from tkinter import messagebox
import math

# ------------------------- Shared Functions -------------------------
def show_option_dialog(question, on_yes, on_no):
    """Show a yes/no dialog box"""
    popup = tk.Toplevel(root)
    popup.title("Confirm Option")
    tk.Label(popup, text=question, font=("Arial", 12)).pack(pady=10)
    btn_frame = tk.Frame(popup)
    btn_frame.pack(pady=5)
    tk.Button(btn_frame, text="Yes", width=10, command=lambda: [on_yes(), popup.destroy()]).pack(side=tk.LEFT, padx=5)
    tk.Button(btn_frame, text="No", width=10, command=lambda: [on_no(), popup.destroy()]).pack(side=tk.LEFT, padx=5)

def display_vhdl(code):
    """Display generated VHDL code in the output text box"""
    vhdl_output.config(state=tk.NORMAL)
    vhdl_output.delete(1.0, tk.END)
    vhdl_output.insert(tk.END, code)
    vhdl_output.config(state=tk.DISABLED)

def clear_entries():
    """Clear all input fields and output"""
    input_entries.delete(0, tk.END)
    output_entries.delete(0, tk.END)
    sel_entries.delete(0, tk.END)
    bit_entry.delete(0, tk.END)
    vhdl_output.config(state=tk.NORMAL)
    vhdl_output.delete(1.0, tk.END)
    vhdl_output.config(state=tk.DISABLED)
    mode_check_var.set(False)
    reset_check_var.set(False)
    clk_check_var.set(False)
    enable_check_var.set(False)
    clk_var.set(False)
    rst_var.set(False)
    mode_var.set(False)

# ------------------------- MUX/DEMUX/Encoder/Decoder Functions -------------------------
def detect_and_generate():
    """Detect which component to generate based on inputs/outputs"""
    try:
        inputs = int(input_entries.get())
        outputs = int(output_entries.get())
        sel = sel_entries.get()

        if inputs <= 0 or outputs <= 0:
            messagebox.showerror("Input Error", "Number of inputs and outputs must be greater than 0.")
            return

        if inputs == 1 and outputs > 1:
            show_option_dialog("Include ENABLE in DEMUX?",
                lambda: generate_demux_vhdl_code(inputs, outputs, int(sel), True),
                lambda: generate_demux_vhdl_code(inputs, outputs, int(sel), False))

        elif outputs == 1 and inputs > 1:
            show_option_dialog("Include ENABLE in MUX?",
                lambda: generate_mux_vhdl_code(inputs, outputs, int(sel), True),
                lambda: generate_mux_vhdl_code(inputs, outputs, int(sel), False))

        elif outputs == 2 ** inputs:
            ask_decoder_feature_options(inputs)

        elif inputs == 2 ** outputs:
            include_enable = enable_check_var.get()
            generate_encoder_vhdl_code(outputs, include_enable)

        else:
            messagebox.showerror("Unknown Configuration", "The configuration does not match any known module.")

    except Exception as e:
        messagebox.showerror("Error", f"An error occurred: {e}")

def ask_decoder_feature_options(num_inputs):
    """Ask about additional decoder features"""
    def proceed():
        generate_decoder_vhdl_code(num_inputs)
    if mode_check_var.get() or reset_check_var.get() or clk_check_var.get() or enable_check_var.get():
        show_option_dialog("Do you want to add selected features (MODE, CLK, RST, EN) to Decoder?", lambda: None, proceed)
    else:
        proceed()

def generate_decoder_vhdl_code(num_inputs):
    """Generate decoder VHDL code"""
    try:
        num_outputs = 2 ** num_inputs
        vhdl_code = f"""library ieee;
use ieee.std_logic_1164.all;

entity Decoder_{num_inputs}x{num_outputs} is
    port (
        input_bits : in std_logic_vector({num_inputs - 1} downto 0);
        decoder_out : out std_logic_vector({num_outputs - 1} downto 0)
    );
end entity;

architecture behavior of Decoder_{num_inputs}x{num_outputs} is
begin
    process (input_bits)
    begin
        case input_bits is
"""
        for i in range(num_outputs):
            vhdl_code += f'            when "{bin(i)[2:].zfill(num_inputs)}" => decoder_out <= "{"0"*i + "1" + "0"*(num_outputs-i-1)}";\n'
        vhdl_code += f"""            when others => decoder_out <= (others => '0');
        end case;
    end process;
end architecture;"""

        display_vhdl(vhdl_code)
    except Exception as e:
        messagebox.showerror("Error", f"Decoder generation failed: {e}")

def generate_encoder_vhdl_code(num_outputs, include_enable):
    """Generate encoder VHDL code"""
    try:
        num_inputs = 2 ** num_outputs
        port_lines = ""
        if include_enable:
            port_lines += "        enable_in : in std_logic;\n"
        port_lines += f"""        encoder_in : in std_logic_vector({num_inputs - 1} downto 0);
        encoder_out : out std_logic_vector({num_outputs - 1} downto 0)"""

        sensitivity = "enable_in, encoder_in" if include_enable else "encoder_in"

        vhdl_code = f"""library ieee;
use ieee.std_logic_1164.all;

entity Encoder_{num_inputs}X{num_outputs} is
    port (
{port_lines}
    );
end entity;

architecture behav of Encoder_{num_inputs}X{num_outputs} is
begin
    process ({sensitivity})
    begin
"""
        if include_enable:
            vhdl_code += "        if (enable_in = '1') then\n"

        vhdl_code += "            case (encoder_in) is\n"
        for i in range(num_inputs):
            bin_val = format(i, f'0{num_outputs}b')
            pattern = '"' + ('0'*i + '1' + '0'*(num_inputs - i -1)).zfill(num_inputs) + '"'
            vhdl_code += f'                when {pattern} => encoder_out <= "{bin_val}";\n'
        vhdl_code += f"""                when others => encoder_out <= (others => '0');
            end case;
"""
        if include_enable:
            vhdl_code += "        else\n            encoder_out <= (others => '0');\n        end if;\n"

        vhdl_code += f"""    end process;
end architecture;"""

        display_vhdl(vhdl_code)
    except Exception as e:
        messagebox.showerror("Error", f"Encoder generation failed: {e}")

def generate_mux_vhdl_code(num_inputs, num_outputs, select_signals, include_enable):
    """Generate multiplexer VHDL code"""
    try:
        required_sel = math.ceil(math.log2(num_inputs))
        if select_signals != required_sel:
            messagebox.showerror("Input Error", f"For {num_inputs} inputs, sel must be {required_sel}.")
            return

        enable_line = "enable : in std_logic;\n        " if include_enable else ""
        vhdl_code = f"""library IEEE;
use IEEE.STD_LOGIC_1164.ALL;

entity mux is
    port (
        selector : in std_logic_vector({select_signals-1} downto 0);
        input : in std_logic_vector({num_inputs-1} downto 0);
        {enable_line}output : out std_logic
    );
end mux;

architecture Behavioral of mux is
begin
    process (selector, input{', enable' if include_enable else ''})
    begin
        {"if enable = '1' then" if include_enable else ''}
        case selector is
"""
        for i in range(num_inputs):
            vhdl_code += f'            when "{bin(i)[2:].zfill(select_signals)}" => output <= input({i});\n'
        vhdl_code += f"""            when others => output <= '0';
        end case;
        {"else\n            output <= '0';\n        end if;" if include_enable else ''}
    end process;
end Behavioral;"""

        display_vhdl(vhdl_code)
    except Exception as e:
        messagebox.showerror("Error", f"MUX generation failed: {e}")

def generate_demux_vhdl_code(num_inputs, num_outputs, select_signals, include_enable):
    """Generate demultiplexer VHDL code"""
    try:
        required_sel = math.ceil(math.log2(num_outputs))
        if select_signals != required_sel:
            messagebox.showerror("Input Error", f"For {num_outputs} outputs, sel must be {required_sel}.")
            return

        outputs = [f"out{i} : out std_logic_vector({num_inputs-1} downto 0)" for i in range(num_outputs)]
        port_lines = ",\n        ".join(outputs)
        if include_enable:
            port_lines += ",\n        enable : in std_logic"

        vhdl_code = f"""library IEEE;
use IEEE.STD_LOGIC_1164.ALL;

entity de_mux is 
    port (
        selector : in std_logic_vector({select_signals-1} downto 0);
        input : in std_logic_vector({num_inputs-1} downto 0);
        {port_lines}
    );
end de_mux; 

architecture Behavioral of de_mux is
begin
    process (selector, input{', enable' if include_enable else ''})
    begin
        {"if enable = '1' then" if include_enable else ''}
        case selector is
"""
        for i in range(num_outputs):
            vhdl_code += f'            when "{bin(i)[2:].zfill(select_signals)}" => out{i} <= input;\n'
        vhdl_code += f"""            when others => null;
        end case;
    end process;
end Behavioral;"""
        display_vhdl(vhdl_code)
    except Exception as e:
        messagebox.showerror("Error", f"DEMUX generation failed: {e}")

# ------------------------- PISO/SIPO Functions -------------------------
def generate_vhdl_code():
    """Generate PISO or SIPO VHDL code based on mode selection"""
    try:
        num_bits = int(bit_entry.get())
        if num_bits <= 0:
            messagebox.showerror("Input Error", "Number of bits must be greater than 0.")
            return

        if not clk_var.get() or not rst_var.get():
            messagebox.showwarning("Missing Signals", "Clock and Reset must be selected to generate code.")
            return

        if mode_var.get():
            # PISO (Parallel-In Serial-Out)
            vhdl_code = f"""library ieee;
use ieee.std_logic_1164.all;

entity PISO_REG is
    port ( Data_in : in std_logic_vector ({num_bits - 1} downto 0);
           MODE, CLK, Reset : in std_logic;
           Ser_Out : out std_logic
         );
end PISO_REG;

architecture Behavior of PISO_REG is
begin
    process (CLK, MODE, Data_in, Reset)
        variable VAR2 : std_logic_vector ({num_bits - 1} downto 0) := (others => '0');
    begin
        if Reset = '1' then
            VAR2 := (others => '0');
            Ser_Out <= '0';
        elsif rising_edge(CLK) then
            case MODE is
                when '1' => -- load parallel Sig_Data
                    VAR2 := Data_in;
                    Ser_Out <= VAR2({num_bits - 1});
                when '0' => -- shifting to left
                    VAR2 := VAR2({num_bits - 2} downto 0) & '0';
                    Ser_Out <= VAR2({num_bits - 1});
                when others => null; -- U or X etc
            end case;
        end if;
    end process;
end architecture;"""
        else:
            # SIPO (Serial-In Parallel-Out)
            vhdl_code = f"""library ieee;
use ieee.std_logic_1164.all;

entity SIPO is
    port ( SER_IN, clk, reset : in STD_LOGIC;
           Parallel_OUT : out STD_LOGIC_VECTOR({num_bits - 1} downto 0)
         );
end SIPO;

architecture Arch of SIPO is
begin
    process (clk, SER_IN, reset)
        variable Var1 : std_logic_vector({num_bits - 1} downto 0) := (others => '0');
    begin
        if (reset = '1') then
            Var1 := (others => '0');
        elsif rising_edge(clk) then
            Var1 := SER_IN & Var1({num_bits - 1} downto 1);
            Parallel_OUT <= Var1;
        end if;
    end process;
end Arch;"""

        display_vhdl(vhdl_code)
    except ValueError:
        messagebox.showerror("Input Error", "Please enter a valid integer for bit width.")

# ------------------------- GUI Setup -------------------------
root = tk.Tk()
root.title("VHDL Code Generator")

# Create notebook for tabs
notebook = tk.ttk.Notebook(root)
notebook.pack(pady=10, expand=True)

# Tab 1: MUX/DEMUX/Encoder/Decoder
tab1 = tk.Frame(notebook)
notebook.add(tab1, text="Combinational")

# Input fields for tab1
tk.Label(tab1, text="Number of Inputs").grid(row=0, column=0)
input_entries = tk.Entry(tab1)
input_entries.grid(row=0, column=1)

tk.Label(tab1, text="Number of Outputs").grid(row=1, column=0)
output_entries = tk.Entry(tab1)
output_entries.grid(row=1, column=1)

tk.Label(tab1, text="Number of Select Signals").grid(row=2, column=0)
sel_entries = tk.Entry(tab1)
sel_entries.grid(row=2, column=1)

# Checkboxes for tab1
mode_check_var = tk.BooleanVar()
# tk.Checkbutton(tab1, text="MODE", variable=mode_check_var).grid(row=3, column=0)

# reset_check_var = tk.BooleanVar()
# tk.Checkbutton(tab1, text="RST", variable=reset_check_var).grid(row=3, column=1)

# clk_check_var = tk.BooleanVar()
# tk.Checkbutton(tab1, text="CLK", variable=clk_check_var).grid(row=4, column=0)

enable_check_var = tk.BooleanVar()
tk.Checkbutton(tab1, text="ENABLE", variable=enable_check_var).grid(row=4, column=1)

# Tab 2: PISO/SIPO
tab2 = tk.Frame(notebook)
notebook.add(tab2, text="Shift Registers")

# Input fields for tab2
tk.Label(tab2, text="Number of Bits:").grid(row=0, column=0, padx=10, pady=5)
bit_entry = tk.Entry(tab2)
bit_entry.grid(row=0, column=1, padx=10, pady=5)

# Checkboxes for tab2
clk_var = tk.BooleanVar()
rst_var = tk.BooleanVar()
mode_var = tk.BooleanVar()

tk.Checkbutton(tab2, text="Clock", variable=clk_var).grid(row=1, column=0, sticky="w", padx=10)
tk.Checkbutton(tab2, text="Reset", variable=rst_var).grid(row=2, column=0, sticky="w", padx=10)
tk.Checkbutton(tab2, text="MODE", variable=mode_var).grid(row=3, column=0, sticky="w", padx=10)

# Buttons for both tabs
button_frame = tk.Frame(root)
button_frame.pack(pady=10)

tk.Button(button_frame, text="Generate VHDL", command=lambda: detect_and_generate() if notebook.index("current") == 0 else generate_vhdl_code()).pack(side=tk.LEFT, padx=5)
tk.Button(button_frame, text="Clear", command=clear_entries).pack(side=tk.LEFT, padx=5)

# Output text area
vhdl_output = tk.Text(root, height=20, width=80, wrap=tk.WORD)
vhdl_output.pack(pady=10)
vhdl_output.config(state=tk.DISABLED)

root.mainloop()