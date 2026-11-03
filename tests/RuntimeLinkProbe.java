package org.connectwow.tests;

/** Diagnostic main for a separate JVM. Never initializes OEM classes or devices. */
public final class RuntimeLinkProbe {
    public static void main(String[] args) {
        int failed = 0;
        System.out.println(new StringBuffer("RUNTIME class.version=")
            .append(System.getProperty("java.class.version")).toString());
        for (int i = 0; i < args.length; i++) {
            try {
                Class type = Class.forName(args[i], false, null);
                // Resolve member signatures without running a class initializer.
                int methods = type.getDeclaredMethods().length;
                int fields = type.getDeclaredFields().length;
                int constructors = type.getDeclaredConstructors().length;
                System.out.println(new StringBuffer("LINK_PASS ").append(args[i])
                    .append(" methods=").append(methods).append(" fields=").append(fields)
                    .append(" constructors=").append(constructors).toString());
            } catch (Throwable error) {
                failed++;
                System.out.println(new StringBuffer("LINK_FAIL ").append(args[i]).append(' ')
                    .append(error.getClass().getName()).append(": ").append(error.getMessage()).toString());
            }
        }
        System.out.println(new StringBuffer("LINK_SUMMARY failures=").append(failed).toString());
        System.exit(failed == 0 ? 0 : 1);
    }
}
