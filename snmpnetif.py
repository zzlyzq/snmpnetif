#!/usr/bin/env python
__ver__ = "30052011"
__doc__ = """
snmpnetif.py
    Author      - rob0r - github.com/rob0r
    Tool to probe network devices for interface statistics via SNMP
    Requires the net-snmp python bindings
"""

class main():
    def __init__(self):
        # try and import netsnmp module
        try:
            import netsnmp
            self.netsnmp = netsnmp
        except:
            print('Failed to load netsnmp module, Is it installed?\n')
            print('Ubuntu users : sudo apt-get install libsnmp-python')
            print('Fedora users : yum install net-snmp-python')
            exit()
        # import the timedate module, used in the devuptime() method
        import datetime
        self.datetime = datetime
        
        # handle CLI arguments
        if __name__ == '__main__':
            import platform
            try:
                import argparse
            except:
                print('Failed to load Python - Argparse module, Is it installed?\n')
                print('Ubuntu users : sudo apt-get install python-argparse')
                exit()
            # the argparse module creates the --help, -h option by default
            cliopts = argparse.ArgumentParser(
                usage = "pysnmpnetif.py",
                epilog = "common usage: snmpnetif.py --target x.x.x.x"
                )
            cliopts.add_argument('--appver',
                help = 'snmpnetif.py version information', 
                action = 'version', 
                version = """
                    snmpnetif.py version: {displayver}
                    platform            : {platform}
                    """.format(displayver = __ver__, platform = platform.platform())
                )
            cliopts.add_argument('--debugcli',
                default = '0',
                choices = '1',
                help = 'run the printargs function (Default: 0)'
                )
            cliopts.add_argument('--target',
                help = 'Host or IP'
                )
            cliopts.add_argument('--community',
                default = 'public',
                help = 'SNMP community string (Default: public)'
                )
            cliopts.add_argument('--port',
                default = '161',
                help = 'SNMP port (Default: 161)',
                type = int
                )
            cliopts.add_argument('--ver',
                default = 'v2c',
                help = 'SNMP version (Default: v2c), Other option is v1',
                type = str
                )
            cliopts.add_argument('--poll',
                default = 2,
                choices = ['1', '2', '3', '5', '10'],
                help = 'Polling rate in seconds (Default: 2)'
                )
            self.args = cliopts.parse_args()
            
            if 'debugcli' in self.args.__dict__:
                if self.args.__dict__['debugcli'] == '1':
                    self.printargs()
                    quit()
            
            # convert snmp version to something useful
            # also handle dud user entry by converting it to the default
            if self.args.__dict__['ver'] == 'v2c':
                self.args.__dict__['ver'] = 2
            elif self.args.__dict__['ver'] == 'v1':
                self.args.__dict__['ver'] = 1
            else:
                self.args.__dict__['ver'] = 2

            # if a target is given create snmp sesion and run probe
            if self.args.__dict__['target'] != None:
                self.session = netsnmp.Session(
                    DestHost = self.args.__dict__['target'], 
                    Version = self.args.__dict__['ver'], 
                    RemotePort = self.args.__dict__['port'], 
                    Community = self.args.__dict__['community']
                    )
                self.probe(float(self.args.__dict__['poll']))
            else:
                print('\nNo target specified!')
                print('See --help for options.\n')

    def printargs(self):
        """
        this method is used for debugging cli arguments
        run snmpnetif.py with --debugcli 1
        """
        print(self.args.__dict__)

    def devname(self):
        """
        this method returns sysDescr.0 data
        """
        oid = self.netsnmp.VarList('iso.3.6.1.2.1.1.1.0')
        name = self.session.get(oid)
        if name == None:
            print('Failed to get device name, Aborting'); quit()
        return name[0]

    def devuptime(self):
        """
        this method returns device uptime worked out from sysUpTimeInstance
        as a datetime.timedelta object
        """
        oid = self.netsnmp.VarList('iso.3.6.1.2.1.1.3.0')
        uptimeticksraw = self.session.get(oid)
        if uptimeticksraw[0] == None:
            print('Failed to get device uptime, Aborting'); quit()
        uptimeticks = int(uptimeticksraw[0])
        uptime = self.datetime.timedelta(seconds = (uptimeticks / 100))
        return uptime

    def ifactive(self):
        """
        this method returns a tuple of interface index numbers
        that have IF-MIB::ifInOctets.x > 0 - This means the interface has 
        had traffic inbound
        """
        oid = self.netsnmp.VarList('iso.3.6.1.2.1.2.2.1.10')
        ifaces = self.session.walk(oid)
        if ifaces == ():
            print('Failed to get device interfaces, Aborting'); quit()
        idx = 1
        ifaceidx = []
        for iface in ifaces:
            if(int(iface) > 0):
                ifaceidx.append(idx)
            idx += 1
        return tuple(ifaceidx)

    def ifnames(self, ifidx):
        """
        this method returns a list of interface name(s)
        ifidx should be a tuple of interface index numbers
        """
        oidbase = 'iso.3.6.1.2.1.2.2.1.2.'
        ifoids = [(oidbase + str(idx)) for idx in ifidx]
        oids = self.netsnmp.VarList(*ifoids)
        ifnames = self.session.get(oids)
        if ifnames[0] == None:
            print('Failed to get interface names, Aborting'); quit()
        return ifnames
        
    def ifoctets(self, inout, ifidx):
        """
        this method returns a list of interface IF-MIB::if[In/Out]Octets values
        inout should be (0 for InOctets, 1 for OutOctets)
        ifidx should be a tuple of interface index numbers
        """
        if inout == 0: oidbase = 'iso.3.6.1.2.1.2.2.1.10.'
        if inout == 1: oidbase = 'iso.3.6.1.2.1.2.2.1.16.'
        ifoids = [(oidbase + str(idx)) for idx in ifidx]
        oids = self.netsnmp.VarList(*ifoids)
        ifoctets = self.session.get(oids)
        if ifoctets[0] == None:
            print('Failed to get interface octets, Aborting'); quit()
        return ifoctets

    def adslsync(self, updown):
        """
        this method returns the transmission speeds
        found at transmission.94.1.1.4.1.2.3 (down)
        and transmission.94.1.1.5.1.2.3 (up). updown should be
        0 for downstream, 1 for upstream
        """
        if updown == 0: oidtree = 'iso.3.6.1.2.1.10.94.1.1.4.1.2'
        if updown == 1: oidtree = 'iso.3.6.1.2.1.10.94.1.1.5.1.2'
        oid = self.netsnmp.VarList(oidtree)
        syncspeed = self.session.walk(oid)
        if syncspeed != ():
            return syncspeed
        else:
            raise Exception
        
    def adslsnr(self, updown):
        """
        this method returns the transmission SNR
        found at transmission.94.1.1.2.1.4.3 (down)
        and transmission.94.1.1.3.1.4.3 (up). updown should be
        0 for downstream, 1 for upstream
        """
        if updown == 0: oidtree = 'iso.3.6.1.2.1.10.94.1.1.2.1.4'
        if updown == 1: oidtree = 'iso.3.6.1.2.1.10.94.1.1.3.1.4'
        oid = self.netsnmp.VarList(oidtree)
        snr = self.session.walk(oid)
        if snr != ():
            return snr
        else:
            raise Exception
    
    def adslattn(self, updown):
        """
        this method returns the transmission Attenuation
        found at transmission.94.1.1.2.1.5.3 (down)
        and transmission.94.1.1.3.1.5.3 (up). updown should be
        0 for downstream, 1 for upstream
        """
        if updown == 0: oidtree = 'iso.3.6.1.2.1.10.94.1.1.2.1.5'
        if updown == 1: oidtree = 'iso.3.6.1.2.1.10.94.1.1.3.1.5'
        oid = self.netsnmp.VarList(oidtree)
        attn = self.session.walk(oid)
        if attn != ():
            return attn
        else:
            raise Exception

    def probe(self, poll):
        """
        this method runs the show :)
        """
        import time
        import os
        import sys
        
        # set first run = True, only display iface stats after the first run
        firstrun = True
        
        # get device name, print during loop
        devicename = self.devname()
        if devicename == None:
            print('Failed to get device name, Aborting'); quit()
        
        # get active interface index list, use during loop
        ifidx = self.ifactive()
        
        # get active interface names
        ifnames = self.ifnames(ifidx)
        
        while(True):
            try:
                # clear the screen
                if os.name == 'nt': clearscreen = os.system('cls')
                if os.name == 'posix': clearscreen = os.system('clear')
                
                # print the device name and uptime
                print(devicename)
                print('Device uptime: {0}\n').format(self.devuptime())
                
                # print stats if the first loop has run
                if firstrun == True:
                    firstrun = False
                    donttrydsl = False
                    print('Collecting Data')
                    print('\nPlease wait {0} secconds').format(poll)
                else:
                    print(str('Interface(s)').ljust(60) + str('Down').rjust(10) + str('Up').rjust(16))
                    print(str('-'*14).ljust(60) + str('-'*4).rjust(10) + str('-'*4).rjust(17))
                    index = 0
                    for interface in ifnames:
                        inspeed_avg[index] = round(inspeed_avg[index], 2)
                        outspeed_avg[index] = round(outspeed_avg[index], 2)
                        print('{0} {1} kB/sec {2} kB/sec').format(
                            str(interface).ljust(60), str(inspeed_avg[index]).rjust(7),
                            str(outspeed_avg[index]).rjust(10)
                            )
                        index += 1
                    # if a DSL probe doesn't throw an exception
                    # DSL stats get displayed
                    if displaydslstats == True:
                        dslidx = 0
                        print(str('\nDSL(s)').ljust(60) + str('Down').rjust(11) + str('Up').rjust(16))
                        print(str('-'*14).ljust(60) + str('-'*4).rjust(10) + str('-'*4).rjust(17))
                        print('Line: {0}').format(dslidx),
                        for dslline in dslsyncdown:
                            print('{0} {1} bps {2} bps').format(
                                str('sync: ').rjust(47),
                                dslsyncdown[dslidx].rjust(12),
                                dslsyncup[dslidx].rjust(13)
                                )
                            print('{0} {1} dB {2} dB').format(
                                str('snr : ').rjust(55),
                                str(float(dslsnrdown[dslidx])/10).rjust(12),
                                str(float(dslsnrup[dslidx])/10).rjust(14)
                                )
                            print('{0} {1} dB {2} dB').format(
                                str('attn: ').rjust(55),
                                str(float(dslattndown[dslidx])/10).rjust(12),
                                str(float(dslattnup[dslidx])/10).rjust(14),
                                '\n'
                                )
                            dslidx += 1
                    print('\n\nData collection is taking: {0} seconds').format(str(round((ttime - poll), 2)))
                    print('Polling every: {0} seconds').format(poll)

                # start the data collection timer
                stime = time.time()
                
                # get in / out octets for active interfaces before the sleep
                inoctets_start = self.ifoctets(0, ifidx)
                outoctets_start = self.ifoctets(1, ifidx)
                
                # sleep for the poll duration
                time.sleep(poll)
                
                # get in / out octets for active interfaces after the sleep
                inoctets_end = self.ifoctets(0, ifidx)
                outoctets_end = self.ifoctets(1, ifidx)
                
                # end the data collection timer
                etime = time.time()
                ttime = etime - stime
                
                # for each interface
                # work out the difference between the start / end octets
                # then divide by total time time to get average octets/sec
                # then divide by 1024 to change to kbytes/sec
                # add to [in/out]speed_avg lists for display
                inspeed_avg = [((int(inoctets_end[x]) - int(inoctets_start[x])) / ttime / 1024) for x in xrange(0, len(ifidx))]
                outspeed_avg = [((int(outoctets_end[x]) - int(outoctets_start[x])) / ttime / 1024) for x in xrange(0, len(ifidx))]
                
                # try probe for DSL stats and set the display flag
                # if first attempt fails, dont keep trying
                if donttrydsl == False:
                    try:
                        dslsyncdown = self.adslsync(0)
                        dslsyncup = self.adslsync(1)
                        dslsnrdown = self.adslsnr(0)
                        dslsnrup = self.adslsnr(1)
                        dslattndown = self.adslattn(0)
                        dslattnup = self.adslattn(1)
                        displaydslstats = True
                    except:
                        displaydslstats = False
                        donttrydsl = True
                
            except KeyboardInterrupt:
                print('\nTerminated'); quit()

if __name__ in '__main__':
    snmpnetif_runapp = main()