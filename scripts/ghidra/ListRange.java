// Print a listing for [start, end): instructions (disassembling on demand), function entries,
// and raw words where nothing decodes. Usage (postScript): ListRange.java <hexstart> <hexend> [...]
//@category MoveTheBox
import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.*;
import ghidra.program.model.address.*;

public class ListRange extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] a = getScriptArgs();
        Listing l = currentProgram.getListing();
        for (int k = 0; k + 1 < a.length; k += 2) {
            Address cur = toAddr(Long.parseLong(a[k], 16));
            Address end = toAddr(Long.parseLong(a[k + 1], 16));
            while (cur.compareTo(end) < 0) {
                Function f = getFunctionAt(cur);
                if (f != null) println("L ---- " + f.getName() + " ----");
                Instruction ins = l.getInstructionAt(cur);
                if (ins == null && l.getDefinedDataAt(cur) == null) { disassemble(cur); ins = l.getInstructionAt(cur); }
                if (ins != null) {
                    println("L " + cur + "\t" + ins);
                    cur = cur.add(ins.getLength());
                } else {
                    println(String.format("L %s\t.word 0x%04x", cur, getShort(cur) & 0xffff));
                    cur = cur.add(2);
                }
            }
        }
    }
}
