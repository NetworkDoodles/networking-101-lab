#!/bin/sh
# Sets a host up when the lab starts (containerlab runs `start <role>` on each host).
# The hosts have no management port: eth1 is their only network card, as on a real computer.
set -e
# IPv4 only, as in the lessons: no IPv6 addresses to read past.
sysctl -qw net.ipv6.conf.all.disable_ipv6=1 net.ipv6.conf.default.disable_ipv6=1 2>/dev/null || true
# containerlab gives the card a second, internal name; a real computer's card has just the one.
for a in $(ip -o link show eth1 | grep -o 'altname [^ ]*' | cut -d' ' -f2); do ip link property del dev eth1 altname "$a"; done
ip link set eth1 up
case "$1" in
  laptop)
    # A DHCP client, as on any laptop: it asks for an address now and renews the lease on its own.
    udhcpc -i eth1 -b -p /run/udhcpc.pid -x hostname:laptop >/var/log/udhcpc.log 2>&1
    ;;
  printer)
    ip addr add 192.168.1.20/24 dev eth1
    ip route add default via 192.168.1.1
    echo "nameserver 192.168.2.53" > /etc/resolv.conf
    ;;
  broken-pc)
    # Someone typed this one in by hand, and got it wrong (task 2.2).
    ip addr add 192.168.1.30/16 dev eth1
    echo "nameserver 192.168.2.53" > /etc/resolv.conf
    ;;
  web)
    ip addr add 192.168.2.10/28 dev eth1
    ip route add default via 192.168.2.1
    echo "nameserver 192.168.2.53" > /etc/resolv.conf
    mkdir -p /srv/www && echo "Hello from web.lab, 192.168.2.10" > /srv/www/index.html
    httpd -h /srv/www
    ;;
  dns)
    ip addr add 192.168.2.53/28 dev eth1
    ip route add default via 192.168.2.49
    echo "nameserver 127.0.0.1" > /etc/resolv.conf
    # Answers for the lab's names from the files in /etc/lab-dns (lab/dns/ in the repo), and re-reads
    # them on its own whenever one changes. It asks nobody else: the lab has no internet.
    dnsmasq --no-resolv --no-hosts --hostsdir=/etc/lab-dns --domain=lab --local=/lab/ --interface=eth1 --local-ttl=60 \
            --log-queries --log-facility=/var/log/dnsmasq.log
    ;;
esac
