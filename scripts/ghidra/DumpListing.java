// Headless helper: disassemble from given entry points and print "addr<TAB>instruction".
// Usage (postScript): DumpListing.java <hexaddr> [<hexaddr> ...]
//@category MoveTheBox
import ghidra.app.script.GhidraScript;
import ghidra.app.cmd.disassemble.DisassembleCommand;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Instruction;

public class DumpListing extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        for (String a : args) {
            Address start = toAddr(Long.parseLong(a, 16));
            new DisassembleCommand(start, null, true).applyTo(currentProgram, monitor);
        }
        println("LANG " + currentProgram.getLanguageID());
        for (Instruction ins : currentProgram.getListing().getInstructions(true)) {
            println("INS " + ins.getAddress() + "\t" + ins.toString());
        }
    }
}
