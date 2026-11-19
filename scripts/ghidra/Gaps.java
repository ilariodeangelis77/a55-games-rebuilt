// Print address ranges in [start,end) that are not covered by instructions or defined data.
// Usage (postScript): Gaps.java <hexstart> <hexend>
//@category MoveTheBox
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.*;
import ghidra.program.model.listing.*;

public class Gaps extends GhidraScript {
    @Override
    public void run() throws Exception {
        Address s = toAddr(Long.parseLong(getScriptArgs()[0], 16));
        Address e = toAddr(Long.parseLong(getScriptArgs()[1], 16));
        AddressSet all = new AddressSet(s, e.subtract(1));
        Listing l = currentProgram.getListing();
        AddressSet used = new AddressSet();
        for (CodeUnit cu : l.getCodeUnits(all, true)) {
            if (cu instanceof Instruction || (cu instanceof Data && ((Data) cu).isDefined()))
                used.add(cu.getMinAddress(), cu.getMaxAddress());
        }
        for (AddressRange r : all.subtract(used)) {
            if (r.getLength() >= 8) println(String.format("GAP %s-%s len=0x%x", r.getMinAddress(), r.getMaxAddress(), r.getLength()));
        }
        for (Function f : currentProgram.getFunctionManager().getFunctions(all, true))
            println("FUNC " + f.getEntryPoint() + " " + f.getBody().getMinAddress() + "-" + f.getBody().getMaxAddress());
    }
}
