import java.nio.file.*;
import java.util.*;
import java.util.jar.*;
import jdk.internal.org.objectweb.asm.*;
import jdk.internal.org.objectweb.asm.tree.*;
import jdk.internal.org.objectweb.asm.tree.analysis.*;

/** Offline-only builder; input is the exact, locally recovered Porsche classes. */
public final class BuildPorscheHooks {
    static final String LAYOUT = "de/audi/tghu/navi/app/map/gui/layout/LayoutProviderG22Kombi";
    static final String CLUSTER = "de/audi/tghu/navi/app/cluster/ClusterService";
    static final String CALLBACK = "org/connectwow/carplay/PorscheGeometry";
    static final String CARPLAY = "de/audi/app/terminalmode/smartphone/carplay/CarPlayDSIManager";
    static final String DISPLAY = "de/audi/tghu/fwhmi/DisplayManagerMIB2High";
    static final String COMBI = "de/audi/tghu/navi/app/cluster/CombiBAPListener";
    static final String ROUTER = "org/connectwow/carplay/PorscheCluster";
    static final String CONTROLS = "org/connectwow/carplay/PorscheClusterControls";
    static final String GUIDANCE = "de/audi/tghu/navi/app/cluster/PorscheRouteGuidance";
    static final String APPSTATE = "org/dsi/ifc/carplay/AppState";
    static int areaHooks, visibilityHooks, activityHooks, contextHooks, switchHooks, scaleHooks, scaleSettingHooks, guidanceHooks, appStateHooks;

    static byte[] neutralizeNavigationOwnership(byte[] input) {
        ClassNode node = new ClassNode();
        new ClassReader(input).accept(node, 0);
        if (!APPSTATE.equals(node.name)) throw new IllegalArgumentException("Wrong CarPlay AppState class");
        boolean speechFound = false;
        for (MethodNode method : node.methods) {
            if (method.name.equals("getSpeechMode") && method.desc.equals("()I")) speechFound = true;
            if ((method.name.equals("getAppStateID") || method.name.equals("getOwner")) && method.desc.equals("()I")) {
                method.instructions.clear();
                method.tryCatchBlocks.clear();
                method.localVariables = null;
                method.instructions.add(new InsnNode(Opcodes.ICONST_0));
                method.instructions.add(new InsnNode(Opcodes.IRETURN));
                method.maxStack = 1;
                appStateHooks++;
            }
        }
        if (!speechFound || appStateHooks != 2) throw new IllegalStateException("Unexpected Porsche CarPlay AppState API");
        ClassWriter writer = new ClassWriter(ClassWriter.COMPUTE_MAXS);
        node.accept(writer);
        byte[] result = writer.toByteArray();
        if ((((result[6] & 255) << 8) | (result[7] & 255)) > Opcodes.V1_4) {
            result[6] = 0;
            result[7] = (byte) Opcodes.V1_4;
        }
        verify(result, true);
        return result;
    }

    static byte[] patch(byte[] input, final String target) {
        ClassReader reader = new ClassReader(input);
        if (!target.equals(reader.getClassName())) throw new IllegalArgumentException("Wrong OEM class");
        ClassWriter writer = new ClassWriter(reader, ClassWriter.COMPUTE_MAXS);
        reader.accept(new ClassVisitor(Opcodes.ASM8, writer) {
            public MethodVisitor visitMethod(int access, String name, String desc, String sig, String[] exceptions) {
                MethodVisitor next = super.visitMethod(access, name, desc, sig, exceptions);
                final boolean area = target.equals(LAYOUT) && name.equals("getVisibleArea")
                    && (desc.equals("(IZZZ)Lorg/dsi/ifc/map/Rect;") || desc.equals("(IZZ)Lorg/dsi/ifc/map/Rect;"));
                final boolean visible = target.equals(CLUSTER) && name.equals("showKombiMap") && desc.equals("(Z)V");
                final boolean activity = target.equals(CARPLAY) && (name.equals("activate") || name.equals("deactivate")) && desc.equals("()V");
                final boolean contexts = target.equals(DISPLAY) && name.equals("defineContexts") && desc.equals("()V");
                final boolean switching = target.equals(DISPLAY) && name.equals("switchContext") && desc.equals("(IILde/audi/atip/hmi/view/IDisplayListener;)V");
                final boolean scale = target.equals(COMBI) && name.equals("setMapScale") && desc.equals("(I)V");
                final boolean scaleSetting = target.equals(COMBI) && name.equals("setMapScaleSetting") && desc.equals("(I)V");
                final boolean guidance = target.equals(CLUSTER) && name.equals("setCombiBAPService")
                    && desc.equals("(Lde/audi/atip/interapp/combi/bap/navi/CombiBAPServiceNavi;)V");
                if (!area && !visible && !activity && !contexts && !switching && !scale && !scaleSetting && !guidance) return next;
                return new MethodVisitor(Opcodes.ASM8, next) {
                    public void visitCode() {
                        super.visitCode();
                        if (switching) {
                            super.visitVarInsn(Opcodes.ILOAD, 1);
                            super.visitVarInsn(Opcodes.ILOAD, 2);
                            super.visitMethodInsn(Opcodes.INVOKESTATIC, ROUTER, "selectContext", "(II)I", false);
                            super.visitVarInsn(Opcodes.ISTORE, 1);
                            switchHooks++;
                        }
                        if (scale) {
                            // Route only the native map side effect to CarPlay. Keep
                            // Porsche's last valid scale and send its mandatory ACK;
                            // incrementing the hidden CarPlay context makes MU1417
                            // report "---" and auto zoom as unavailable.
                            Label stock = new Label();
                            super.visitVarInsn(Opcodes.ILOAD, 1);
                            super.visitMethodInsn(Opcodes.INVOKESTATIC, CONTROLS, "consumeMapScale", "(I)Z", false);
                            super.visitJumpInsn(Opcodes.IFEQ, stock);
                            super.visitVarInsn(Opcodes.ALOAD, 0);
                            super.visitMethodInsn(Opcodes.INVOKEVIRTUAL, COMBI, "updateMapScale", "()V", false);
                            super.visitInsn(Opcodes.RETURN);
                            super.visitLabel(stock);
                            scaleHooks++;
                        }
                        if (scaleSetting) {
                            // Observe only. No public reference proves a universal
                            // CarPlay auto-zoom command, so the complete OEM method
                            // always remains authoritative.
                            super.visitVarInsn(Opcodes.ILOAD, 1);
                            super.visitMethodInsn(Opcodes.INVOKESTATIC, CONTROLS, "consumeMapScaleSetting", "(I)Z", false);
                            super.visitInsn(Opcodes.POP);
                            scaleSettingHooks++;
                        }
                    }
                    public void visitInsn(int opcode) {
                        if (area && opcode == Opcodes.ARETURN) {
                            // Leave the original return value untouched below the observer arguments.
                            super.visitInsn(Opcodes.DUP);
                            super.visitVarInsn(Opcodes.ALOAD, 0);
                            super.visitInsn(Opcodes.SWAP);
                            super.visitVarInsn(Opcodes.ALOAD, 0);
                            super.visitFieldInsn(Opcodes.GETFIELD, LAYOUT, "kombiType", "I");
                            super.visitMethodInsn(Opcodes.INVOKESTATIC, CALLBACK, "observe",
                                "(Lde/audi/tghu/navi/app/map/gui/layout/AbstractLayoutProvider;Lorg/dsi/ifc/map/Rect;I)V", false);
                            areaHooks++;
                        }
                        if (visible && opcode == Opcodes.RETURN) {
                            super.visitVarInsn(Opcodes.ILOAD, 1);
                            super.visitMethodInsn(Opcodes.INVOKESTATIC, CALLBACK, "setVisible", "(Z)V", false);
                            visibilityHooks++;
                        }
                        if (activity && opcode == Opcodes.RETURN) {
                            super.visitVarInsn(Opcodes.ALOAD, 0);
                            super.visitFieldInsn(Opcodes.GETFIELD, CARPLAY, "active", "Z");
                            super.visitMethodInsn(Opcodes.INVOKESTATIC, CALLBACK, "setCarPlayActive", "(Z)V", false);
                            activityHooks++;
                        }
                        if (contexts && opcode == Opcodes.RETURN) {
                            super.visitVarInsn(Opcodes.ALOAD, 0);
                            super.visitFieldInsn(Opcodes.GETFIELD, DISPLAY, "dc", "[Lorg/dsi/ifc/displaymanagement/DisplayContext;");
                            super.visitMethodInsn(Opcodes.INVOKESTATIC, ROUTER, "installContexts", "([Lorg/dsi/ifc/displaymanagement/DisplayContext;)V", false);
                            contextHooks++;
                        }
                        if (guidance && opcode == Opcodes.RETURN) {
                            super.visitVarInsn(Opcodes.ALOAD, 0);
                            super.visitFieldInsn(Opcodes.GETFIELD, CLUSTER, "combiBAPListener", "Lde/audi/tghu/navi/app/cluster/CombiBAPListener;");
                            super.visitMethodInsn(Opcodes.INVOKESTATIC, GUIDANCE, "attach", "(Lde/audi/tghu/navi/app/cluster/CombiBAPListener;)V", false);
                            guidanceHooks++;
                        }
                        super.visitInsn(opcode);
                    }
                };
            }
        }, ClassReader.SKIP_FRAMES);
        byte[] result = writer.toByteArray();
        // Preserve the recovered attribute encoding and method bodies. This
        // exact header normalization (including both formerly version-49 OEM
        // classes) passed the physical J9 VM's isolated -Xverify:all link probe.
        int major = ((result[6] & 255) << 8) | (result[7] & 255);
        if (major > Opcodes.V1_4) {
            result[6] = 0;
            result[7] = (byte) Opcodes.V1_4;
        }
        verify(result, true);
        return result;
    }

    static void verify(byte[] data, boolean all) {
        ClassNode node = new ClassNode();
        new ClassReader(data).accept(node, ClassReader.SKIP_FRAMES);
        for (MethodNode method : node.methods) {
            if ((method.access & (Opcodes.ACC_ABSTRACT | Opcodes.ACC_NATIVE)) != 0) continue;
            if (!all && !method.name.equals("getVisibleArea") && !method.name.equals("showKombiMap") && !method.name.equals("activate") && !method.name.equals("deactivate")) continue;
            try { new Analyzer<BasicValue>(new BasicVerifier()).analyze(node.name, method); }
            catch (AnalyzerException e) { throw new IllegalStateException(node.name + "." + method.name, e); }
        }
    }

    static byte[] legacy(byte[] input) {
        ClassWriter writer = new ClassWriter(0);
        new ClassReader(input).accept(new ClassVisitor(Opcodes.ASM8, writer) {
            public void visit(int v, int a, String n, String s, String p, String[] i) {
                super.visit(Opcodes.V1_2, a, n, s, p, i);
            }
        }, ClassReader.SKIP_FRAMES);
        byte[] data = writer.toByteArray();
        String raw = new String(data, java.nio.charset.StandardCharsets.ISO_8859_1);
        for (String bad : new String[]{"java/lang/StringBuilder", "java/nio/", "java/lang/invoke/"})
            if (raw.contains(bad)) throw new IllegalStateException("Unsupported CDC dependency: " + bad);
        verify(data, true);
        return data;
    }

    static void add(JarOutputStream out, String name, byte[] data) throws Exception {
        JarEntry entry = new JarEntry(name); entry.setTime(0); out.putNextEntry(entry); out.write(data); out.closeEntry();
    }

    static void checkApi(JarFile original) throws Exception {
        ClassNode layout = new ClassNode(), rect = new ClassNode(), combi = new ClassNode();
        new ClassReader(original.getInputStream(original.getJarEntry(
            "de/audi/tghu/navi/app/map/gui/layout/AbstractLayoutProvider.class"))).accept(layout, 0);
        for (String name : new String[]{"getScreenWidth", "getScreenHeight"}) {
            boolean found = false;
            for (MethodNode method : layout.methods)
                if (method.name.equals(name) && method.desc.equals("()I") && (method.access & Opcodes.ACC_PUBLIC) != 0) found = true;
            if (!found) throw new IllegalStateException("OEM API mismatch: " + name);
        }
        new ClassReader(original.getInputStream(original.getJarEntry("org/dsi/ifc/map/Rect.class"))).accept(rect, 0);
        for (String name : new String[]{"kordX", "kordY", "diffX", "diffY"}) {
            boolean found = false;
            for (FieldNode field : rect.fields)
                if (field.name.equals(name) && field.desc.equals("I") && (field.access & Opcodes.ACC_PUBLIC) != 0) found = true;
            if (!found) throw new IllegalStateException("OEM Rect mismatch: " + name);
        }
        new ClassReader(original.getInputStream(original.getJarEntry(COMBI + ".class"))).accept(combi, 0);
        boolean street = false;
        for (MethodNode method : combi.methods)
            if (method.name.equals("setCurrentStreet") && method.desc.equals("(Ljava/lang/String;)V")) street = true;
        if (!street) throw new IllegalStateException("OEM API mismatch: setCurrentStreet(String)");
    }

    public static void main(String[] args) throws Exception {
        Path classes = Path.of(args[1]);
        byte[] notificationClass = null;
        try (JarFile original = new JarFile(args[0]); JarOutputStream out = new JarOutputStream(Files.newOutputStream(Path.of(args[2])))) {
            checkApi(original);
            // Keep the global AppState replacement out of the main bridge.
            // AppState is shared by every HMI application; preloading the
            // notification compatibility patch here can prevent unrelated
            // OSGi bundles from starting. It is emitted only in the separate
            // notification probe JAR below.
            for (String name : new String[]{LAYOUT, CLUSTER, CARPLAY, DISPLAY, COMBI}) {
                JarEntry entry = original.getJarEntry(name + ".class");
                if (entry == null) throw new IllegalStateException("Missing exact Porsche class: " + name);
                byte[] source = original.getInputStream(entry).readAllBytes();
                byte[] result = patch(source, name);
                add(out, name + ".class", result);
            }
            try (var stream = Files.walk(classes.resolve("org/connectwow/carplay"))) {
                for (Path file : stream.filter(p -> p.toString().endsWith(".class")).sorted().toList())
                    add(out, classes.relativize(file).toString().replace('\\', '/'), legacy(Files.readAllBytes(file)));
            }
            Path guidanceDirectory = classes.resolve("de/audi/tghu/navi/app/cluster");
            try (var stream = Files.list(guidanceDirectory)) {
                List<Path> guidanceClasses = stream
                    .filter(p -> p.getFileName().toString().startsWith("PorscheRouteGuidance") &&
                                 p.getFileName().toString().endsWith(".class"))
                    .sorted().toList();
                if (guidanceClasses.size() != 3)
                    throw new IllegalStateException("Unexpected PorscheRouteGuidance class set: " + guidanceClasses);
                for (Path file : guidanceClasses)
                    add(out, classes.relativize(file).toString().replace('\\', '/'),
                        legacy(Files.readAllBytes(file)));
            }
        }
        if (args.length >= 4) {
            try (JarFile original = new JarFile(args[0])) {
                JarEntry entry = original.getJarEntry(APPSTATE + ".class");
                if (entry == null) throw new IllegalStateException("Missing exact Porsche class: " + APPSTATE);
                notificationClass = neutralizeNavigationOwnership(original.getInputStream(entry).readAllBytes());
            }
            try (JarOutputStream notifications = new JarOutputStream(Files.newOutputStream(Path.of(args[3])))) {
                add(notifications, APPSTATE + ".class", notificationClass);
            }
        }
        if (areaHooks != 2 || visibilityHooks != 1 || activityHooks != 4 || contextHooks != 1 || switchHooks != 1 || scaleHooks != 1 || scaleSettingHooks != 1 || guidanceHooks != 1 || appStateHooks != 2) throw new IllegalStateException("Unexpected Porsche hook layout");
        System.out.println("Porsche bridge: display, route guidance and background CarPlay notifications; all method bytecode checked");
    }
}
