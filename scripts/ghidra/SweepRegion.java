// Linear-sweep disassembly of gaps in [start,end): repeatedly disassemble at the first byte of
// every uncovered range (word aligned, skipping 0xFFFF filler) until nothing changes, then create
// functions at CALLS targets inside the region. Usage (preScript): SweepRegion.java <hexstart> <hexend>
//@category MoveTheBox
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.*;
import ghidra.program.model.listing.*;
import ghidra.program.model.symbol.*;

public class SweepRegion extends GhidraScript {
    @Override
    public void run() throws Exception {
        Address s = toAddr(Long.parseLong(getScriptArgs()[0], 16));
        Address e = toAddr(Long.parseLong(getScriptArgs()[1], 16));
        Listing l = currentProgram.getListing();
        int passes = 0, total = 0;
        boolean changed = true;
        while (changed && passes < 50) {
            changed = false; passes++;
            AddressSet all = new AddressSet(s, e.subtract(1));
            AddressSet used = new AddressSet();
            for (CodeUnit cu : l.getCodeUnits(all, true))
                if (cu instanceof Instruction || (cu instanceof Data && ((Data) cu).isDefined()))
                    used.add(cu.getMinAddress(), cu.getMaxAddress());
            for (AddressRange r : all.subtract(used)) {
                Address a = r.getMinAddress();
                if ((a.getOffset() & 1) != 0) a = a.add(1);
                while (a.compareTo(r.getMaxAddress()) < 0 && (getShort(a) & 0xffff) == 0xffff) a = a.add(2);
                if (a.compareTo(r.getMaxAddress()) >= 0) continue;
                if (l.getInstructionAt(a) == null && disassemble(a)) { changed = true; total++; }
            }
        }
        int f = 0;
        ReferenceManager rm = currentProgram.getReferenceManager();
        for (Instruction ins : l.getInstructions(new AddressSet(s, e.subtract(1)), true)) {
            if (!ins.getFlowType().isCall()) continue;
            for (Address t : ins.getFlows()) {
                if (t.compareTo(s) >= 0 && t.compareTo(e) < 0 && getFunctionAt(t) == null && createFunction(t, null) != null) f++;
            }
        }
        println("sweep passes=" + passes + " disassembly starts=" + total + " new functions=" + f);
    }
}
