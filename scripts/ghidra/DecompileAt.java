// Headless: decompile functions at the given hex addresses (creating them if needed).
// Usage (postScript): DecompileAt.java <hexaddr> [...]
//@category MoveTheBox
import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.*;
import ghidra.program.model.listing.*;
import ghidra.program.model.address.*;

public class DecompileAt extends GhidraScript {
    @Override
    public void run() throws Exception {
        DecompInterface di = new DecompInterface();
        di.openProgram(currentProgram);
        for (String a : getScriptArgs()) {
            Address addr = toAddr(Long.parseLong(a.replace("0x", ""), 16));
            Function f = getFunctionContaining(addr);
            if (f == null) { disassemble(addr); f = createFunction(addr, null); }
            if (f == null) { println("no function at " + a); continue; }
            DecompileResults res = di.decompileFunction(f, 120, monitor);
            println("===== FUNCTION " + f.getName() + " @ " + f.getEntryPoint());
            println(res.decompileCompleted() ? res.getDecompiledFunction().getC() : "decompile failed: " + res.getErrorMessage());
        }
    }
}
