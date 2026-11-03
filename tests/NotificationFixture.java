import java.lang.reflect.Constructor;
import java.lang.reflect.Method;

/** Build-time proof that navigation ownership is neutralized but speech survives. */
public final class NotificationFixture {
    public static void main(String[] args) throws Exception {
        Class<?> type = Class.forName("org.dsi.ifc.carplay.AppState");
        Constructor<?> constructor = type.getConstructor(Integer.TYPE, Integer.TYPE, Integer.TYPE);
        Object state = constructor.newInstance(Integer.valueOf(3), Integer.valueOf(2), Integer.valueOf(3));
        assertValue(type, state, "getAppStateID", 0);
        assertValue(type, state, "getOwner", 0);
        assertValue(type, state, "getSpeechMode", 3);
        System.out.println("PORSCHE_NOTIFICATION_PASS navigation ownership neutral, speech and popup path retained");
    }

    private static void assertValue(Class<?> type, Object state, String methodName, int expected) throws Exception {
        Method method = type.getMethod(methodName);
        int actual = ((Integer) method.invoke(state)).intValue();
        if (actual != expected) throw new IllegalStateException(methodName + "=" + actual + ", expected " + expected);
    }
}
