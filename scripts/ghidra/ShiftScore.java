// Rank functions in [start,end) by number of shift/rotate/bit-test instructions (decompressor hunt).
// Usage (postScript): ShiftScore.java <hexstart> <hexend> [topN]
//@category MoveTheBox
import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.*;
import ghidra.program.model.address.*;
import java.util.*;

public class ShiftScore extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] a = getScriptArgs();
        Address s = toAddr(Long.parseLong(a[0], 16)), e = toAddr(Long.parseLong(a[1], 16));
        int top = a.length > 2 ? Integer.parseInt(a[2]) : 25;
        List<long[]> res = new ArrayList<>();
        for (Function f : currentProgram.getFunctionManager().getFunctions(new AddressSet(s, e), true)) {
            int sh = 0, n = 0;
            for (Instruction i : currentProgram.getListing().getInstructions(f.getBody(), true)) {
                n++;
                String m = i.getMnemonicString().toLowerCase();
                if (m.startsWith("shl") || m.startsWith("shr") || m.startsWith("rol") || m.startsWith("ror") || m.startsWith("ashr")) sh++;
            }
            if (sh >= 4) res.add(new long[]{sh, n, f.getEntryPoint().getOffset()});
        }
        res.sort((x, y) -> Long.compare(y[0] * 1000 / Math.max(1, y[1]), x[0] * 1000 / Math.max(1, x[1])));
        for (int k = 0; k < Math.min(top, res.size()); k++)
            println(String.format("F %06x shifts=%d instrs=%d", res.get(k)[2], res.get(k)[0], res.get(k)[1]));
    }
}
