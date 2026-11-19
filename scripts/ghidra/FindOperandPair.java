// List instructions in [start,end) whose text contains A, followed within N instructions by one containing B.
// Usage (postScript): FindOperandPair.java <hexstart> <hexend> <A> <B> [N]
//@category MoveTheBox
import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.*;
import ghidra.program.model.address.*;

public class FindOperandPair extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] a = getScriptArgs();
        Address s = toAddr(Long.parseLong(a[0], 16)), e = toAddr(Long.parseLong(a[1], 16));
        int n = a.length > 4 ? Integer.parseInt(a[4]) : 4;
        Listing l = currentProgram.getListing();
        for (Instruction ins : l.getInstructions(new AddressSet(s, e), true)) {
            if (!ins.toString().contains(a[2])) continue;
            Instruction j = ins.getNext();
            for (int k = 0; k < n && j != null; k++, j = j.getNext()) {
                if (j.toString().contains(a[3])) {
                    Function f = getFunctionContaining(ins.getAddress());
                    println("HIT " + ins.getAddress() + " " + ins + " | " + j + " in " + (f == null ? "?" : f.getName()));
                    break;
                }
            }
        }
    }
}
