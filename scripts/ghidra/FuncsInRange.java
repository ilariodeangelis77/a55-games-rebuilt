// List functions with entry in [start,end): entry, body size, callers count, callees.
// Usage (postScript): FuncsInRange.java <hexstart> <hexend>
//@category MoveTheBox
import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.*;
import ghidra.program.model.address.*;
import java.util.*;

public class FuncsInRange extends GhidraScript {
    @Override
    public void run() throws Exception {
        Address s = toAddr(Long.parseLong(getScriptArgs()[0], 16));
        Address e = toAddr(Long.parseLong(getScriptArgs()[1], 16));
        for (Function f : currentProgram.getFunctionManager().getFunctions(new AddressSet(s, e), true)) {
            Set<Function> callers = f.getCallingFunctions(monitor);
            Set<Function> callees = f.getCalledFunctions(monitor);
            StringBuilder sb = new StringBuilder();
            for (Function c : callees) sb.append(c.getEntryPoint()).append(' ');
            StringBuilder cb = new StringBuilder();
            for (Function c : callers) cb.append(c.getEntryPoint()).append(' ');
            println(String.format("F %s size=%d callers=[%s] callees=[%s]", f.getEntryPoint(), f.getBody().getNumAddresses(), cb.toString().trim(), sb.toString().trim()));
        }
    }
}
