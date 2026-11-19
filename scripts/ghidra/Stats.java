// Print function/instruction counts and the listing of the first N instructions from given addresses.
// Usage (postScript): Stats.java [<hexaddr> <count>] ...
//@category MoveTheBox
import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.*;
import ghidra.program.model.address.*;

public class Stats extends GhidraScript {
    @Override
    public void run() throws Exception {
        Listing l = currentProgram.getListing();
        println("functions=" + currentProgram.getFunctionManager().getFunctionCount()
                + " instructions=" + l.getNumInstructions());
        String[] a = getScriptArgs();
        for (int i = 0; i + 1 < a.length; i += 2) {
            Address addr = toAddr(Long.parseLong(a[i], 16));
            int n = Integer.parseInt(a[i + 1]);
            Instruction ins = l.getInstructionAt(addr);
            if (ins == null) { disassemble(addr); ins = l.getInstructionAt(addr); }
            for (int k = 0; k < n && ins != null; k++) {
                println("INS " + ins.getAddress() + "\t" + ins);
                ins = ins.getNext();
            }
        }
    }
}
