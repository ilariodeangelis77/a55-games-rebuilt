// Disassemble and create functions at every hex address listed (one per line) in the given file.
// Usage (preScript): SeedFromList.java <file>
//@category MoveTheBox
import ghidra.app.script.GhidraScript;
import ghidra.app.cmd.disassemble.DisassembleCommand;
import ghidra.program.model.address.*;
import java.nio.file.*;

public class SeedFromList extends GhidraScript {
    @Override
    public void run() throws Exception {
        AddressSet set = new AddressSet();
        int n = 0;
        for (String line : Files.readAllLines(Paths.get(getScriptArgs()[0]))) {
            line = line.trim();
            if (line.isEmpty()) continue;
            Address a = toAddr(Long.parseLong(line, 16));
            set.add(a);
            n++;
        }
        DisassembleCommand cmd = new DisassembleCommand(set, null, true);
        cmd.applyTo(currentProgram, monitor);
        int f = 0;
        for (AddressRange r : set) {
            Address a = r.getMinAddress();
            if (getFunctionAt(a) == null && getInstructionAt(a) != null && createFunction(a, null) != null) f++;
        }
        println("seeded " + n + " addresses, created " + f + " functions");
    }
}
