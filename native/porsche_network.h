#ifndef CW_PORSCHE_NETWORK_H
#define CW_PORSCHE_NETWORK_H
/* MU1417 efs-system.img, /etc/pf.conf:
 * carplay0 permits TCP 7000:7001, then drops all other inbound traffic.
 * en0/debug permits TCP 22110:22111, then drops other inbound traffic.
 * No firewall configuration is changed by this implementation. */
#define CW_CARPLAY_DATA_PORT 7001
#define CW_DIAGNOSTIC_UPLOAD_PORT 22110
#endif
