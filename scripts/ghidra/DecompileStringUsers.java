// Headless: for each substring argument, find defined strings containing it, then decompile
// every function that references those strings. Prints C to stdout.
// Usage (postScript): DecompileStringUsers.java "<substr>" ["<substr>" ...]
//@category MoveTheBox
import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.*;
import ghidra.program.model.listing.*;
import ghidra.program.model.symbol.*;
import ghidra.program.model.address.*;
import java.util.*;

public class DecompileStringUsers extends GhidraScript {
    @Override
    public void run() throws Exception {
        DecompInterface di = new DecompInterface();
        di.openProgram(currentProgram);
        Set<Function> done = new LinkedHashSet<>();
        for (String needle : getScriptArgs()) {
            for (Data d : currentProgram.getListing().getDefinedData(true)) {
                Object v = d.getValue();
                if (!(v instanceof String) || !((String) v).contains(needle)) continue;
                println("STRING " + d.getAddress() + " \"" + v + "\"");
                for (Reference r : getReferencesTo(d.getAddress())) {
                    Function f = getFunctionContaining(r.getFromAddress());
                    if (f == null) { println("  ref from " + r.getFromAddress() + " (no function)"); continue; }
                    println("  ref from " + r.getFromAddress() + " in " + f.getName() + " @ " + f.getEntryPoint());
                    done.add(f);
                }
            }
        }
        for (Function f : done) {
            DecompileResults res = di.decompileFunction(f, 120, monitor);
            println("===== FUNCTION " + f.getName() + " @ " + f.getEntryPoint());
            println(res.decompileCompleted() ? res.getDecompiledFunction().getC() : "decompile failed: " + res.getErrorMessage());
        }
    }
}
