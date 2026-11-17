import java.nio.file.*;
import java.util.*;
import java.util.jar.*;
import jdk.internal.org.objectweb.asm.*;
import jdk.internal.org.objectweb.asm.tree.*;
import jdk.internal.org.objectweb.asm.tree.analysis.*;

/** Separate opt-in candidate; never overwrites the ordinary split artifacts. */
public final class BuildNavigationPriority {
 static final String R="de/audi/tghu/navi/app/cluster/NavigationPriorityRuntime";
 static final String G="de/audi/tghu/navi/app/cluster/PorscheRouteGuidance";
 static final String C="de/audi/tghu/navi/app/cluster/CombiBAPListener";
 static final String S="de/audi/tghu/navi/app/cluster/ClusterService";
 static final String D="de/audi/tghu/navi/app/dsi/DSINavigationDispatcher";
 static int bapHooks,guidanceHooks,pollHooks,routeHooks,clusterHooks,readyHooks,orphanGeometryHooks;
 static void call(MethodVisitor v,String name,String desc){v.visitMethodInsn(Opcodes.INVOKESTATIC,R,name,desc,false);}
 static void loadArgs(MethodVisitor v,MethodNode m){int slot=(m.access&Opcodes.ACC_STATIC)==0?1:0;
  if(slot==1)v.visitVarInsn(Opcodes.ALOAD,0);
  for(Type t:Type.getArgumentTypes(m.desc)){v.visitVarInsn(t.getOpcode(Opcodes.ILOAD),slot);slot+=t.getSize();}
 }
 static int slots(MethodNode m){int n=(m.access&Opcodes.ACC_STATIC)==0?1:0;for(Type t:Type.getArgumentTypes(m.desc))n+=t.getSize();return n;}
 static MethodNode wrapBap(ClassNode n,MethodNode m,boolean guarded){
  String name=m.name;int access=m.access;String original="cwOriginal$"+name;
  m.name=original;m.access=(access&Opcodes.ACC_SYNCHRONIZED)|Opcodes.ACC_PRIVATE;
  MethodNode w=new MethodNode(Opcodes.ASM8,access&~Opcodes.ACC_SYNCHRONIZED,name,m.desc,m.signature,m.exceptions.toArray(new String[0]));
  int ticket=slots(w),error=ticket+1;MethodVisitor v=w;v.visitCode();
  v.visitInsn(guarded?Opcodes.ICONST_1:Opcodes.ICONST_0);call(v,"beginBap","(Z)I");v.visitVarInsn(Opcodes.ISTORE,ticket);
  Label start=new Label(),end=new Label(),finish=new Label(),handler=new Label();
  v.visitVarInsn(Opcodes.ILOAD,ticket);v.visitJumpInsn(Opcodes.IFNE,start);v.visitInsn(Opcodes.RETURN);
  v.visitLabel(start);loadArgs(v,w);v.visitMethodInsn(Opcodes.INVOKESPECIAL,n.name,original,m.desc,false);
  v.visitLabel(end);v.visitJumpInsn(Opcodes.GOTO,finish);
  v.visitLabel(handler);v.visitVarInsn(Opcodes.ASTORE,error);v.visitVarInsn(Opcodes.ILOAD,ticket);call(v,"endBap","(I)V");v.visitVarInsn(Opcodes.ALOAD,error);v.visitInsn(Opcodes.ATHROW);
  v.visitLabel(finish);v.visitVarInsn(Opcodes.ILOAD,ticket);call(v,"endBap","(I)V");v.visitInsn(Opcodes.RETURN);
  v.visitTryCatchBlock(start,end,handler,null);v.visitMaxs(0,0);v.visitEnd();return w;
 }
 static void leave(MethodVisitor v,int op){v.visitLdcInsn(op);v.visitFieldInsn(Opcodes.GETSTATIC,G,"active","Z");v.visitFieldInsn(Opcodes.GETSTATIC,G,"clearPending","Z");call(v,"leave","(IZZ)V");}
 static MethodNode wrapGuidance(ClassNode n,MethodNode m,int op){
  String name=m.name,original="cwOriginal$"+name;int access=m.access;m.name=original;
  MethodNode w=new MethodNode(Opcodes.ASM8,access,name,m.desc,m.signature,m.exceptions.toArray(new String[0]));
  MethodVisitor v=w;int lock=slots(w),entered=lock+1,error=lock+2;
  v.visitCode();v.visitInsn(Opcodes.ICONST_0);v.visitVarInsn(Opcodes.ISTORE,entered);
  v.visitFieldInsn(Opcodes.GETSTATIC,R,"LOCK","Ljava/lang/Object;");v.visitInsn(Opcodes.DUP);v.visitVarInsn(Opcodes.ASTORE,lock);v.visitInsn(Opcodes.MONITORENTER);
  Label start=new Label(),end=new Label(),finish=new Label(),handler=new Label(),noLeave=new Label(),noErrorLeave=new Label();v.visitLabel(start);
  v.visitLdcInsn(op);if(op==0){v.visitVarInsn(Opcodes.ALOAD,0);v.visitFieldInsn(Opcodes.GETFIELD,G+"$State","active","Z");}else v.visitInsn(Opcodes.ICONST_0);
  call(v,"enter","(IZ)Z");v.visitJumpInsn(Opcodes.IFEQ,end);v.visitInsn(Opcodes.ICONST_1);v.visitVarInsn(Opcodes.ISTORE,entered);
  loadArgs(v,w);v.visitMethodInsn(Opcodes.INVOKESTATIC,n.name,original,m.desc,false);
  v.visitLabel(end);v.visitJumpInsn(Opcodes.GOTO,finish);
  v.visitLabel(handler);v.visitVarInsn(Opcodes.ASTORE,error);v.visitVarInsn(Opcodes.ILOAD,entered);v.visitJumpInsn(Opcodes.IFEQ,noErrorLeave);leave(v,op);v.visitLabel(noErrorLeave);
  v.visitVarInsn(Opcodes.ALOAD,lock);v.visitInsn(Opcodes.MONITOREXIT);v.visitVarInsn(Opcodes.ALOAD,error);v.visitInsn(Opcodes.ATHROW);
  v.visitLabel(finish);v.visitVarInsn(Opcodes.ILOAD,entered);v.visitJumpInsn(Opcodes.IFEQ,noLeave);leave(v,op);v.visitLabel(noLeave);
  v.visitVarInsn(Opcodes.ALOAD,lock);v.visitInsn(Opcodes.MONITOREXIT);v.visitInsn(Opcodes.RETURN);
  v.visitTryCatchBlock(start,end,handler,null);v.visitMaxs(0,0);v.visitEnd();return w;
 }
 static byte[] patch(byte[] data,String name)throws Exception{
  ClassNode n=new ClassNode();new ClassReader(data).accept(n,0);List<MethodNode> add=new ArrayList<>();
  Set<String> fields=Set.of("setRgActive","setGALState","setLaneGuidance","setManeuverDescriptor","setDistanceToNextManeuver","setDestinationInfo","setTurnToInfo","setRgDistanceToNextDestination","setRgTimeToNextDestination","updateBapManeuverState");
  for(MethodNode m:new ArrayList<MethodNode>(n.methods)){
   if(m.name.startsWith("cwOriginal$"))throw new IllegalStateException("Already patched priority input");
   if(name.equals(S)&&m.name.equals("showKombiMap")&&m.desc.equals("(Z)V")){
    // The split baseline retained this observer call but not its class. Native
    // now publishes geometry. Restore only the original OEM method tail;
    // never add the old Java geometry publisher/worker to this candidate.
    for(AbstractInsnNode i:m.instructions.toArray())if(i instanceof MethodInsnNode c
      && c.owner.equals("org/connectwow/carplay/PorscheGeometry")&&c.name.equals("setVisible")&&c.desc.equals("(Z)V")){
     AbstractInsnNode argument=i.getPrevious();
     if(!(argument instanceof VarInsnNode a)||a.getOpcode()!=Opcodes.ILOAD||a.var!=1)
      throw new IllegalStateException("Unknown legacy geometry observer tail");
     m.instructions.remove(argument);m.instructions.remove(i);orphanGeometryHooks++;
    }
   }
   if(name.equals(C)&&(fields.contains(m.name)||(m.access&Opcodes.ACC_SYNCHRONIZED)!=0)){
    if(Type.getReturnType(m.desc).getSort()!=Type.VOID||(m.access&Opcodes.ACC_STATIC)!=0)throw new IllegalStateException("Unexpected synchronized OEM API");
    for(AbstractInsnNode i:m.instructions)if(i.getOpcode()==Opcodes.MONITORENTER)throw new IllegalStateException("Unexpected explicit OEM monitor");
    add.add(wrapBap(n,m,fields.contains(m.name)));bapHooks++;continue;
   }
   if(name.equals(G)&&m.name.equals("update")&&m.desc.equals("(L"+G+"$State;)V")){add.add(wrapGuidance(n,m,0));guidanceHooks++;continue;}
   if(name.equals(G)&&m.name.equals("clear")&&m.desc.equals("(L"+C+";)V")){add.add(wrapGuidance(n,m,1));guidanceHooks++;continue;}
   if(name.equals(G)&&m.name.equals("poll")){
    for(AbstractInsnNode i:m.instructions.toArray())if(i instanceof MethodInsnNode c&&c.owner.equals(G)&&c.name.equals("read")){
     m.instructions.insertBefore(i,new MethodInsnNode(Opcodes.INVOKESTATIC,R,"poll","()V",false));pollHooks++;
    }
   }
   if(name.equals(D)&&m.name.equals("updateRgActive")&&m.desc.equals("(ZI)V")){
    InsnList in=new InsnList();in.add(new VarInsnNode(Opcodes.ILOAD,1));in.add(new VarInsnNode(Opcodes.ILOAD,2));in.add(new MethodInsnNode(Opcodes.INVOKESTATIC,R,"beforeNative","(ZI)V",false));m.instructions.insert(in);routeHooks++;
   }
   if(name.equals(S)&&m.name.equals("updateRgActive")&&m.desc.equals("(Z)V")){
    for(AbstractInsnNode i:m.instructions.toArray())if(i.getOpcode()==Opcodes.RETURN){InsnList in=new InsnList();in.add(new VarInsnNode(Opcodes.ILOAD,1));in.add(new MethodInsnNode(Opcodes.INVOKESTATIC,R,"afterNative","(Z)V",false));m.instructions.insertBefore(i,in);clusterHooks++;}
   }
   if(name.equals("org/connectwow/carplay/PorscheCluster")&&m.name.equals("readyEpoch")&&m.desc.equals("()J")){
    InsnList in=new InsnList();LabelNode allowed=new LabelNode();in.add(new MethodInsnNode(Opcodes.INVOKESTATIC,R,"permitsCarPlay","()Z",false));in.add(new JumpInsnNode(Opcodes.IFNE,allowed));in.add(new InsnNode(Opcodes.LCONST_0));in.add(new InsnNode(Opcodes.LRETURN));in.add(allowed);m.instructions.insert(in);readyHooks++;
   }
  }
  n.methods.addAll(add);
  if(name.equals("org/connectwow/carplay/PorscheClusterControls")){
   MethodNode flush=new MethodNode(Opcodes.ACC_PUBLIC|Opcodes.ACC_STATIC,"cwDiscard","()V",null,null);
   flush.visitCode();flush.visitFieldInsn(Opcodes.GETSTATIC,n.name,"LOCK","Ljava/lang/Object;");flush.visitInsn(Opcodes.DUP);flush.visitVarInsn(Opcodes.ASTORE,0);flush.visitInsn(Opcodes.MONITORENTER);
   Label start=new Label(),end=new Label(),handler=new Label();flush.visitLabel(start);flush.visitMethodInsn(Opcodes.INVOKESTATIC,n.name,"clearLocked","()V",false);flush.visitLabel(end);
   flush.visitVarInsn(Opcodes.ALOAD,0);flush.visitInsn(Opcodes.MONITOREXIT);flush.visitInsn(Opcodes.RETURN);
   flush.visitLabel(handler);flush.visitVarInsn(Opcodes.ASTORE,1);flush.visitVarInsn(Opcodes.ALOAD,0);flush.visitInsn(Opcodes.MONITOREXIT);flush.visitVarInsn(Opcodes.ALOAD,1);flush.visitInsn(Opcodes.ATHROW);flush.visitTryCatchBlock(start,end,handler,null);flush.visitMaxs(0,0);flush.visitEnd();n.methods.add(flush);
  }
  if(name.equals(G)){
   MethodNode clear=new MethodNode(Opcodes.ACC_PUBLIC|Opcodes.ACC_STATIC,"cwPreempt","()V",null,null);clear.visitCode();Label absent=new Label();clear.visitFieldInsn(Opcodes.GETSTATIC,G,"listener","L"+C+";");clear.visitVarInsn(Opcodes.ASTORE,0);clear.visitVarInsn(Opcodes.ALOAD,0);clear.visitJumpInsn(Opcodes.IFNULL,absent);clear.visitVarInsn(Opcodes.ALOAD,0);clear.visitMethodInsn(Opcodes.INVOKESTATIC,G,"clear","(L"+C+";)V",false);clear.visitLabel(absent);clear.visitInsn(Opcodes.RETURN);clear.visitMaxs(0,0);clear.visitEnd();n.methods.add(clear);
   MethodNode reset=new MethodNode(Opcodes.ACC_PUBLIC|Opcodes.ACC_STATIC,"cwReset","()V",null,null);reset.visitCode();
   for(String f:new String[]{"active","clearPending"}){reset.visitInsn(Opcodes.ICONST_0);reset.visitFieldInsn(Opcodes.PUTSTATIC,G,f,"Z");}
   for(String f:new String[]{"appliedEpoch","lastAppliedAt","lastValidReadAt","lastBlinkAt"}){reset.visitLdcInsn(f.equals("appliedEpoch")?-1L:0L);reset.visitFieldInsn(Opcodes.PUTSTATIC,G,f,"J");}
   for(String f:new String[]{"lastDistance","lastCursor","lastRawType","lastMain"}){reset.visitInsn(Opcodes.ICONST_M1);reset.visitFieldInsn(Opcodes.PUTSTATIC,G,f,"I");}
   reset.visitLdcInsn("");reset.visitFieldInsn(Opcodes.PUTSTATIC,G,"lastSemanticKey","Ljava/lang/String;");reset.visitInsn(Opcodes.RETURN);reset.visitMaxs(0,0);reset.visitEnd();n.methods.add(reset);
  }
  ClassWriter w=new ClassWriter(ClassWriter.COMPUTE_MAXS);n.accept(w);byte[] result=w.toByteArray();verify(result);return result;
 }
 static void verify(byte[] bytes)throws Exception{ClassNode n=new ClassNode();new ClassReader(bytes).accept(n,ClassReader.SKIP_FRAMES);for(MethodNode m:n.methods)if((m.access&(Opcodes.ACC_NATIVE|Opcodes.ACC_ABSTRACT))==0)new Analyzer<BasicValue>(new BasicVerifier()).analyze(n.name,m);}
 static byte[] legacy(byte[] bytes)throws Exception{ClassWriter w=new ClassWriter(ClassWriter.COMPUTE_MAXS);new ClassReader(bytes).accept(new ClassVisitor(Opcodes.ASM8,w){public void visit(int v,int a,String n,String s,String p,String[] i){super.visit(Opcodes.V1_2,a,n,s,p,i);}},ClassReader.SKIP_FRAMES);bytes=w.toByteArray();verify(bytes);String raw=new String(bytes,java.nio.charset.StandardCharsets.ISO_8859_1);for(String bad:new String[]{"java/lang/StringBuilder","java/nio/","java/lang/invoke/"})if(raw.contains(bad))throw new IllegalStateException("Non-legacy API: "+bad);return bytes;}
 public static void main(String[] args)throws Exception{
  Map<String,byte[]> entries=new TreeMap<>();for(int a=0;a<3;a++)try(JarFile z=new JarFile(args[a])){for(JarEntry e:Collections.list(z.entries()))if(!e.isDirectory()){byte[] data=z.getInputStream(e).readAllBytes();if(entries.containsKey(e.getName())&&!Arrays.equals(entries.get(e.getName()),data))throw new IllegalStateException("Conflicting source class");entries.put(e.getName(),data);}}
  for(String name:new String[]{C,G,S,D,"org/connectwow/carplay/PorscheCluster","org/connectwow/carplay/PorscheClusterControls"}){byte[] data=entries.get(name+".class");if(data==null)throw new IllegalStateException("Missing class "+name);entries.put(name+".class",patch(data,name));}
  Path classes=Path.of(args[3]);try(var files=Files.walk(classes)){for(Path f:files.filter(p->p.toString().endsWith(".class")).toList()){
   String name=classes.relativize(f).toString().replace('\\','/');if(name.contains("NavigationPriorityRuntime")||name.contains("PorscheNavigationPriority")||name.equals("org/connectwow/tests/RuntimeLinkProbe.class"))entries.put(name,legacy(Files.readAllBytes(f)));
  }}
  if(bapHooks!=12||guidanceHooks!=2||pollHooks!=1||routeHooks!=1||clusterHooks!=1||readyHooks!=1||orphanGeometryHooks!=1)throw new IllegalStateException("Unexpected priority hook counts: "+bapHooks+"/"+guidanceHooks+"/"+pollHooks+"/"+routeHooks+"/"+clusterHooks+"/"+readyHooks+"/"+orphanGeometryHooks);
  try(JarOutputStream out=new JarOutputStream(Files.newOutputStream(Path.of(args[4])))){for(var e:entries.entrySet()){JarEntry entry=new JarEntry(e.getKey());entry.setTime(0L);out.putNextEntry(entry);out.write(e.getValue());out.closeEntry();}}
  System.out.println("PRIORITY_JAVA_BYTECODE_PASS BAP="+bapHooks+" guidance=2 poll=1 native-event=1 native-publish=1 ready=1 orphan-geometry-removed=1");
 }
}
