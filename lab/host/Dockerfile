# The lab's hosts: a small Linux computer with the everyday network tools.
#   ip (iproute2)   addresses, routes and the neighbour (ARP) table
#   ping, traceroute, arp (net-tools), dig and nslookup (bind-tools), curl
#   udhcpc          the DHCP client (part of busybox)
#   dnsmasq, httpd  only the dns and web hosts run these
FROM alpine:3.22
RUN apk add --no-cache bash iproute2 iputils traceroute net-tools bind-tools curl dnsmasq busybox-extras \
 && echo 'PS1="\h:\w# "' > /root/.bashrc
COPY udhcpc.script /usr/share/udhcpc/default.script
COPY start.sh /usr/local/bin/start
CMD ["sleep", "infinity"]
