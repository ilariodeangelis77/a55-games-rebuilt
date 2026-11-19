// Pre-analysis: seed disassembly from the C166 trap/interrupt vector table at the start of flash.
// Each vector slot is 4 bytes; slots holding JMPS (opcode 0xFA seg addrLo addrHi) are followed.
//@category MoveTheBox
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.symbol.SourceType;

public class SeedVectors extends GhidraScript {
    @Override
    public void run() throws Exception {
        Address base = currentProgram.getMinAddress();
        int seeded = 0;
        for (int slot = 0; slot < 0x200; slot += 4) {
            Address a = base.add(slot);
            int op = getByte(a) & 0xff;
            if (op != 0xFA) continue;
            int seg = getByte(a.add(1)) & 0xff;
            int off = (getByte(a.add(2)) & 0xff) | ((getByte(a.add(3)) & 0xff) << 8);
            Address tgt = toAddr(((long) seg << 16) | off);
            disassemble(a);
            if (currentProgram.getMemory().contains(tgt)) {
                disassemble(tgt);
                if (getFunctionAt(tgt) == null) createFunction(tgt, String.format("vec_%02X_%06X", slot / 4, tgt.getOffset()));
                seeded++;
            }
            createLabel(a, String.format("VEC_%02X", slot / 4), true, SourceType.USER_DEFINED);
        }
        println("seeded " + seeded + " vector targets");
    }
}
