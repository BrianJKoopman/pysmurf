import numpy as np
from .logger import SmurfLogger
from pysmurf.command.cryo_card import CryoCard

from pysmurf.util.pub import Publisher

class SmurfBase(object):
    '''
    Base class for common things
    '''

    _base_args = ['verbose', 'logfile', 'log_timestamp', 'log_prefix',
                  'load_configs', 'log', 'layout']

    LOG_USER = 0
    """
    Default log level for user code. DO NOT USE in library
    """
    LOG_ERROR = 0   # deliberately same as LOG_USER
    """
    Only log errors
    """
    LOG_INFO = 1
    """
    Extra high-level information. Configuration notices that happen once
    """
    LOG_TASK = 2
    """
    Overall progress on a task
    """

    def __init__(self, log=None, epics_root=None, offline=False,
                 pub_root=None, script_id=None, **kwargs):
        """
        Opt Arguments
        --------------
        pub_root (str):
            Root of environment vars to set publisher options. If None, the
            default root will be "SMURFPUB_".

        script_id (str):
            Script id included with publisher messages. For example, the
            script or operation name.
        """
        # Set up logging
        self.log = log
        if self.log is None:
            self.log = self.init_log(**kwargs)
        else:
            verb = kwargs.pop('verbose', None)
            if verb is not None:
                self.set_verbose(verb)

        # If <pub_root>BACKEND environment variable is not set to 'udp', all
        # publish calls will be no-ops.
        self.pub = Publisher(env_root=pub_root, script_id=script_id)

        self.offline = offline
        if self.offline == True:
            self.log('Offline mode')


        # Setting paths for easier commands - Is there a better way to do this
        # than just hardcoding paths? This needs to be cleaned up somehow

        self.epics_root = epics_root
        
        self.amcc = self.epics_root + ':AMCc:'
        self.fpga_top_level = self.amcc + 'FpgaTopLevel:'
        self.app_top = self.fpga_top_level + 'AppTop:'        
        self.app_core = self.app_top + 'AppCore:'

        # AppTop
        self.dac_sig_gen = self.app_top + 'DacSigGen[{}]:'
        
        # AppCore
        self.microwave_mux_core = self.app_core + 'MicrowaveMuxCore[{}]:'        
        self.sysgencryo = self.app_core + 'SysgenCryo:'
        self.timing_header = self.app_core + 'TimingHeader:'

        # MicrowaveMuxCore[#]
        self.DBG = self.microwave_mux_core + 'DBG:'
        self.dac_root = self.microwave_mux_core + 'DAC[{}]:'
        self.att_root = self.microwave_mux_core + 'ATT:'

        # LMK
        self.lmk = self.microwave_mux_core + 'LMK:'
        
        # SysgenCryo
        self.band_root = self.sysgencryo + 'Base[{}]:'
        self.adc_root = self.sysgencryo + 'CryoAdcMux:'

        self.cryo_root = self.band_root + 'CryoChannels:'
        self.channel_root = self.cryo_root + 'CryoChannel[{}]:'

        self.streaming_root = self.amcc + 'streamingInterface:'

        # FpgaTopLevel
        self.fpgatl = self.amcc + 'FpgaTopLevel:'

        # AppTop
        self.apptop = self.fpgatl + 'AppTop:'

        # AppCore
        self.appcore = self.apptop + 'AppCore:'        
        
        # AmcCarrierCore
        self.amccc = self.fpgatl + 'AmcCarrierCore:'
        
        # Crossbar
        self.crossbar = self.amccc + 'AxiSy56040:'

        # Regulator
        self.regulator = self.amccc + 'IntelEnpirion:'

        # CarrierBsi
        self.amc_carrier_bsi = self.amccc + 'AmcCarrierBsi:'
        
        # FPGA
        self.ultrascale = self.amccc + 'AxiSysMonUltraScale:'
    
        # Tx -> DAC , Rx <- ADC
        self.axi_version = self.amccc + 'AxiVersion:'
        self.waveform_engine_buffers_root = self.amccc + \
            'AmcCarrierBsa:BsaWaveformEngine[{}]:' + \
            'WaveformEngineBuffers:'
        self.stream_data_writer_root = self.amcc + 'streamDataWriter:'
        self.jesd_tx_root = self.apptop + 'AppTopJesd[{}]:JesdTx:'
        self.jesd_rx_root = self.apptop + 'AppTopJesd[{}]:JesdRx:'
        self.daq_mux_root = self.apptop + 'DaqMuxV2[{}]:'

        # RTM paths
        self.rtm_cryo_det_root = self.appcore + 'RtmCryoDet:'
        self.rtm_spi_root = self.rtm_cryo_det_root + \
            'RtmSpiSr:'
        self.rtm_spi_max_root = self.rtm_cryo_det_root + \
            'RtmSpiMax:'
        self.rtm_spi_cryo_root = self.rtm_cryo_det_root + \
            'SpiCryo:'

        # Timing paths
        self.amctiming = self.amccc + 'AmcCarrierTiming:'
        self.trigger_root =  self.amctiming + 'EvrV2CoreTriggers:'
        self.timing_status = self.amctiming + 'TimingFrameRx:'

        self.C = CryoCard(self.rtm_spi_cryo_root + 'read', 
            self.rtm_spi_cryo_root + 'write')
        self.freq_resp = {}

    def init_log(self, verbose=0, logger=SmurfLogger, logfile=None,
                 log_timestamp=True, log_prefix=None, **kwargs):
        """
        Initialize the logger from the input keyword arguments.

        Arguments
        ---------
        logger : logging class, optional
            Class to initialize, should be a subclass of SmurfLogger
            or equivalent.
        verbose : bool, int, or string; optional
            Verbosity level, non-negative.  Default: 0 (print user-level
            messages only). String options are 'info', 'time', 'gd', or 'samp'.
        logfile : string, optional
            Logging output filename.  Default: None (print to sys.stdout)
        log_timestamp : bool, optional
            If True, add timestamps to log entries. Default: True
        log_prefix : string, optional
            If supplied, this prefix will be pre-pended to log strings,
            before the timestamp.

        Returns
        -------
        log : log object
            Initialized logging object
        """
        if verbose is None:
            verbose = 0

        timestamp = log_timestamp
        prefix = log_prefix
        levels = dict()
        for k in dir(self):
            if not k.startswith('LOG_'):
                continue
            v = getattr(self, k)
            name = k.split('LOG_', 1)[1].lower()
            levels[name] = v
        log = logger(verbosity=verbose, logfile=logfile,
                     timestamp=timestamp, prefix=prefix,
                     levels=levels, **kwargs)
        return log

    def set_verbose(self, level):
        """
        Change verbosity level.  Can be an integer or a string name.
        Valid strings are 'info', 'time', 'gd' or 'samp'.
        """
        self.log.set_verbosity(level)

    def set_logfile(self, logfile=None):
        """
        Change the location where logs are written.  If logfile is None,
        log to STDOUT.
        """
        self.log.set_logfile(logfile)

    def _band_root(self, band):
        '''
        Helper function that returns the epics path to a band.

        Args:
        -----
        band (int): The band to access

        Returns:
        --------
        path (string) : The string to be passed to caget/caput to access
            the input band.
        '''
        return self.band_root.format(int(band))

    def _cryo_root(self, band):
        '''
        Helper function that returns the epics path to cryoroot.

        Args:
        -----
        band (int): The band to access

        Returns:
        --------
        path (string) : The string to be passed to caget/caput to access
            the input band.
        '''
        return self.cryo_root.format(int(band))

    def _channel_root(self, band, channel):
        """
        Helper function that returns the epics path to channel root.

        Args:
        -----
        band (int) : The band to access
        channel (int) : The channel to access.

        Returns:
        --------
        path (string) : The string to be passed to caget/caput to access
            the input band.
        """
        return self.channel_root.format(int(band), int(channel))
