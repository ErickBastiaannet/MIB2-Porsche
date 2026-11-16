import java.nio.file.*;
import jdk.internal.org.objectweb.asm.*;
import jdk.internal.org.objectweb.asm.tree.*;
import jdk.internal.org.objectweb.asm.tree.analysis.*;

/** Offline patch of one BAP output call; never changes stored MapView or zoom. */
public final class BuildSatelliteLogoProbe {
    static final String COMBI = "de/audi/tghu/navi/app/cluster/CombiBAPListener";
    static final String SERVICE = "de/audi/atip/interapp/combi/bap/navi/CombiBAPServiceNavi";
    static final String HELPER = "de/audi/tghu/navi/app/cluster/PorscheSatelliteLogo";
    static void verify(byte[] data) throws Exception {
        ClassNode n = new ClassNode(); new ClassReader(data).accept(n, ClassReader.SKIP_FRAMES);
        for (MethodNode m : n.methods)
            if ((m.access & (Opcodes.ACC_ABSTRACT | Opcodes.ACC_NATIVE)) == 0)
                new Analyzer<BasicValue>(new BasicVerifier()).analyze(n.name, m);
    }
    public static void main(String[] args) throws Exception {
        byte[] input = Files.readAllBytes(Path.of(args[0]));
        ClassNode n = new ClassNode(); new ClassReader(input).accept(n, 0);
        if (!COMBI.equals(n.name)) throw new IllegalArgumentException("Unexpected OEM class");
        int hooks = 0;
        for (MethodNode m : n.methods) {
            if (!m.name.equals("updateMapView") || !m.desc.equals("()V")) continue;
            for (AbstractInsnNode i : m.instructions) {
                if (!(i instanceof MethodInsnNode)) continue;
                MethodInsnNode call = (MethodInsnNode)i;
                if (call.getOpcode() == Opcodes.INVOKEINTERFACE && call.owner.equals(SERVICE)
                    && call.name.equals("updateMapView") && call.desc.equals("(II)V")) {
                    call.setOpcode(Opcodes.INVOKESTATIC); call.owner = HELPER;
                    call.name = "send"; call.desc = "(L" + SERVICE + ";II)V"; call.itf = false;
                    hooks++;
                }
            }
        }
        if (hooks != 1) throw new IllegalStateException("Expected exactly one OEM BAP MapView call");
        ClassWriter w = new ClassWriter(0); n.accept(w);
        byte[] data = w.toByteArray(); verify(data); Files.write(Path.of(args[1]), data);
        for (int a = 2; a < args.length; a++) {
            Path path = Path.of(args[a]); byte[] bytes = Files.readAllBytes(path);
            ClassWriter legacy = new ClassWriter(0);
            new ClassReader(bytes).accept(new ClassVisitor(Opcodes.ASM8, legacy) {
                public void visit(int v,int access,String name,String sig,String parent,String[] interfaces) {
                    super.visit(Opcodes.V1_2,access,name,sig,parent,interfaces);
                }
            }, ClassReader.SKIP_FRAMES);
            bytes = legacy.toByteArray(); verify(bytes);
            String raw = new String(bytes, java.nio.charset.StandardCharsets.ISO_8859_1);
            for (String bad : new String[]{"java/lang/StringBuilder","java/nio/","java/lang/invoke/"})
                if (raw.contains(bad)) throw new IllegalStateException("Unsupported legacy API");
            Files.write(path,bytes);
        }
        System.out.println("SATELLITE_LOGO_PATCH_PASS one outgoing BAP call; stored OEM state unchanged; bytecode verified");
    }
}
