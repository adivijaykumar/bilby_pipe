#!/usr/bin/env python
"""
Module containing the main input class
"""
from __future__ import division, print_function

import os
import glob
import json

import numpy as np
import bilby
import pandas as pd

from . import utils
from .utils import logger, BilbyPipeError, convert_string_to_dict


class Input(object):
    """ Superclass of input handlers """

    @property
    def idx(self):
        """ The level A job index """
        return self._idx

    @idx.setter
    def idx(self, idx):
        self._idx = idx

    @property
    def known_detectors(self):
        try:
            return self._known_detectors
        except AttributeError:
            return ["H1", "L1", "V1"]

    @known_detectors.setter
    def known_detectors(self, known_detectors):
        self._known_detectors = utils.convert_detectors_input(known_detectors)

    @property
    def detectors(self):
        """ A list of the detectors to include, e.g., ['H1', 'L1'] """
        return self._detectors

    @detectors.setter
    def detectors(self, detectors):
        self._detectors = utils.convert_detectors_input(detectors)
        self._check_detectors_against_known_detectors()

    def _check_detectors_against_known_detectors(self):
        for element in self.detectors:
            if element not in self.known_detectors:
                raise BilbyPipeError(
                    'detectors contains "{}" not in the known '
                    "detectors list: {} ".format(element, self.known_detectors)
                )

    @staticmethod
    def _split_string_by_space(string):
        """ Converts "H1 L1" to ["H1", "L1"] """
        return string.split(" ")

    @staticmethod
    def _convert_string_to_list(string):
        """ Converts various strings to a list """
        string = string.replace(",", " ")
        string = string.replace("[", "")
        string = string.replace("]", "")
        string = string.replace('"', "")
        string = string.replace("'", "")
        string_list = string.split()
        return string_list

    @property
    def outdir(self):
        """ The path to the directory where output will be stored """
        return self._outdir

    @outdir.setter
    def outdir(self, outdir):
        self._outdir = os.path.relpath(outdir)
        for dr in [
            outdir,
            self.submit_directory,
            self.data_generation_log_directory,
            self.data_analysis_log_directory,
            self.data_directory,
            self.summary_log_directory,
            self.result_directory,
        ]:
            utils.check_directory_exists_and_if_not_mkdir(dr)

    @property
    def submit_directory(self):
        """ The path to the directory where submit output will be stored """
        return os.path.join(self._outdir, "submit")

    @property
    def data_generation_log_directory(self):
        """ The path to the directory where log output will be stored """
        return os.path.join(self._outdir, "log_data_generation")

    @property
    def data_analysis_log_directory(self):
        """ The path to the directory where log output will be stored """
        return os.path.join(self._outdir, "log_data_analysis")

    @property
    def summary_log_directory(self):
        """ The path to the directory where log output will be stored """
        return os.path.join(self._outdir, "log_results_page")

    @property
    def data_directory(self):
        """ The path to the directory where data output will be stored """
        return os.path.join(self._outdir, "data")

    @property
    def result_directory(self):
        """ The path to the directory where result output will be stored """
        return os.path.join(self._outdir, "result")

    @property
    def webdir(self):
        return self._webdir

    @webdir.setter
    def webdir(self, webdir):
        if webdir is None:
            self._webdir = os.path.join(self.outdir, "results_page")
        else:
            self._webdir = webdir

    @property
    def gps_file(self):
        """ The gps file containing the list of gps times """
        return self._gps_file

    @gps_file.setter
    def gps_file(self, gps_file):
        """ Set the gps_file

        At setting, will check the file exists, read the contents, identify
        which element to generate data for, and create the interferometers.
        """
        if gps_file is None:
            self._gps_file = None
            return
        elif os.path.isfile(gps_file):
            self._gps_file = os.path.relpath(gps_file)
        else:
            raise FileNotFoundError(
                "Input file gps_file={} not understood".format(gps_file)
            )

        if hasattr(self, "_parse_gps_file"):
            self._parse_gps_file()
        else:
            logger.debug("No _parse_gps_file method present")

    def read_gps_file(self):
        gpstimes = np.loadtxt(self.gps_file, ndmin=1)
        return gpstimes

    @property
    def bilby_frequency_domain_source_model(self):
        """ The bilby function to pass to the waveform_generator """
        if self.frequency_domain_source_model in bilby.gw.source.__dict__.keys():
            model = self._frequency_domain_source_model
            logger.info("Using the {} source model".format(model))
            return bilby.gw.source.__dict__[model]
        else:
            raise BilbyPipeError(
                "No source model {} found.".format(self._frequency_domain_source_model)
            )

    @property
    def bilby_roq_frequency_domain_source_model(self):
        if "binary_neutron_star" in self.frequency_domain_source_model:
            logger.info("Using the binary_neutron_star_roq source model")
            return bilby.gw.source.binary_neutron_star_roq
        elif "binary_black_hole" in self.frequency_domain_source_model:
            logger.info("Using the binary_black_hole_roq source model")
            return bilby.gw.source.binary_black_hole_roq
        else:
            BilbyPipeError("Unable to determine roq_source from source model")

    @property
    def frequency_domain_source_model(self):
        """ String of which frequency domain source model to use """
        return self._frequency_domain_source_model

    @frequency_domain_source_model.setter
    def frequency_domain_source_model(self, frequency_domain_source_model):
        self._frequency_domain_source_model = frequency_domain_source_model

    @property
    def trigger_time(self):
        return self._trigger_time

    @trigger_time.setter
    def trigger_time(self, trigger_time):
        self._trigger_time = trigger_time
        if trigger_time is not None:
            logger.info("Setting trigger time {}".format(trigger_time))

    @property
    def start_time(self):
        try:
            return self._start_time
        except AttributeError:
            logger.info("No start-time set, fall back to default start time")
        try:
            self._start_time = (
                self.trigger_time + self.post_trigger_duration - self.duration
            )
            return self._start_time
        except AttributeError:
            logger.warning("Unable to calculate default segment start time")
            return None

    @start_time.setter
    def start_time(self, start_time):
        self._start_time = start_time
        if start_time is not None:
            logger.info("Setting segment start time {}".format(start_time))

    @property
    def duration(self):
        return self._duration

    @duration.setter
    def duration(self, duration):
        self._duration = duration
        if duration is not None:
            logger.info("Setting segment duration {}".format(duration))

    @property
    def injection_file(self):
        return self._injection_file

    @injection_file.setter
    def injection_file(self, injection_file):
        if injection_file is None:
            logger.debug("No injection file set")
            self._injection_file = None
        elif os.path.isfile(injection_file):
            self._injection_file = os.path.relpath(injection_file)
            with open(injection_file, "r") as file:
                injection_dict = json.load(
                    file, object_hook=bilby.core.result.decode_bilby_json
                )
            injection_df = injection_dict["injections"]
            try:
                self.injection_df = pd.DataFrame(injection_df)
            except ValueError:
                self.injection_df = pd.DataFrame(injection_df, index=[0])

            self.total_number_of_injections = len(injection_df)
        else:
            raise FileNotFoundError(
                "Injection file {} not found".format(injection_file)
            )

    @property
    def spline_calibration_envelope_dict(self):
        return self._spline_calibration_envelope_dict

    @spline_calibration_envelope_dict.setter
    def spline_calibration_envelope_dict(self, spline_calibration_envelope_dict):
        if spline_calibration_envelope_dict is not None:
            self._spline_calibration_envelope_dict = convert_string_to_dict(
                spline_calibration_envelope_dict, "spline-calibration-envelope-dict"
            )
        else:
            logger.debug("spline_calibration_envelope_dict")
            self._spline_calibration_envelope_dict = None

    @property
    def spline_calibration_amplitude_uncertainty_dict(self):
        return self._spline_calibration_amplitude_uncertainty_dict

    @spline_calibration_amplitude_uncertainty_dict.setter
    def spline_calibration_amplitude_uncertainty_dict(
        self, spline_calibration_amplitude_uncertainty_dict
    ):
        if spline_calibration_amplitude_uncertainty_dict is not None:
            self._spline_calibration_amplitude_uncertainty_dict = convert_string_to_dict(
                spline_calibration_amplitude_uncertainty_dict,
                "spline-calibration-amplitude-uncertainty-dict",
            )
        else:
            logger.debug("spline_calibration_amplitude_uncertainty_dict")
            self._spline_calibration_amplitude_uncertainty_dict = None

    @property
    def spline_calibration_phase_uncertainty_dict(self):
        return self._spline_calibration_phase_uncertainty_dict

    @spline_calibration_phase_uncertainty_dict.setter
    def spline_calibration_phase_uncertainty_dict(
        self, spline_calibration_phase_uncertainty_dict
    ):
        if spline_calibration_phase_uncertainty_dict is not None:
            self._spline_calibration_phase_uncertainty_dict = convert_string_to_dict(
                spline_calibration_phase_uncertainty_dict,
                "spline-calibration-phase-uncertainty-dict",
            )
        else:
            logger.debug("spline_calibration_phase_uncertainty_dict")
            self._spline_calibration_phase_uncertainty_dict = None

    @property
    def minimum_frequency(self):
        """ The minimum frequency

        If a per-detector dictionary is given, this will return the minimum
        frequency value. To access the dictionary,
        see self.minimum_frequency_dict
        """
        return self._minimum_frequency

    @minimum_frequency.setter
    def minimum_frequency(self, minimum_frequency):
        if minimum_frequency is None:
            self._minimum_frequency = None
            self.minimum_frequency_dict = {det: None for det in self.detectors}
        else:
            try:
                self._minimum_frequency = float(minimum_frequency)
                self.minimum_frequency_dict = {
                    det: float(minimum_frequency) for det in self.detectors
                }
            except ValueError:
                self.minimum_frequency_dict = convert_string_to_dict(
                    minimum_frequency, "minimum-frequency"
                )
                self._minimum_frequency = np.min(
                    [xx for xx in self._minimum_frequency_dict.values()]
                )

    @property
    def minimum_frequency_dict(self):
        return self._minimum_frequency_dict

    @minimum_frequency_dict.setter
    def minimum_frequency_dict(self, minimum_frequency_dict):
        for det in minimum_frequency_dict.keys():
            if det not in self.detectors:
                raise BilbyPipeError(
                    "Input minimum frequency required for detector {}".format(det)
                )
        self._minimum_frequency_dict = minimum_frequency_dict

    @property
    def maximum_frequency(self):
        """ The maximum frequency

        If a per-detector dictionary is given, this will return the maximum
        frequency value. To access the dictionary,
        see self.maximum_frequency_dict
        """

        return self._maximum_frequency

    @maximum_frequency.setter
    def maximum_frequency(self, maximum_frequency):
        if maximum_frequency is None:
            self._maximum_frequency = None
            self.maximum_frequency_dict = {det: None for det in self.detectors}
        else:
            try:
                self._maximum_frequency = float(maximum_frequency)
                self.maximum_frequency_dict = {
                    det: float(maximum_frequency) for det in self.detectors
                }
            except ValueError:
                self.maximum_frequency_dict = convert_string_to_dict(
                    maximum_frequency, "maximum-frequency"
                )
                self._maximum_frequency = np.max(
                    [xx for xx in self._maximum_frequency_dict.values()]
                )

    @property
    def maximum_frequency_dict(self):
        return self._maximum_frequency_dict

    @maximum_frequency_dict.setter
    def maximum_frequency_dict(self, maximum_frequency_dict):
        for det in maximum_frequency_dict.keys():
            if det not in self.detectors:
                raise BilbyPipeError(
                    "Input maximum frequency required for detector {}".format(det)
                )
        self._maximum_frequency_dict = maximum_frequency_dict

    @property
    def default_prior_files(self):
        return self.get_default_prior_files()

    @staticmethod
    def get_default_prior_files():
        """ Returns a dictionary of the default priors """
        prior_files_glob = os.path.join(
            os.path.dirname(os.path.realpath(__file__)), "data_files/*prior"
        )
        filenames = glob.glob(prior_files_glob)
        return {os.path.basename(ff).rstrip(".prior"): ff for ff in filenames}

    def get_distance_file_lookup_table(self, prior_file_str):
        direc = os.path.dirname(self.default_prior_files[prior_file_str])
        fname = "{}_distance_marginalization_lookup.npz".format(prior_file_str)
        return os.path.join(direc, fname)

    @property
    def prior_file(self):
        return self._prior_file

    @prior_file.setter
    def prior_file(self, prior_file):
        if prior_file is None:
            self._prior_file = None
        elif os.path.isfile(prior_file):
            self._prior_file = prior_file
        elif os.path.isfile(os.path.basename(prior_file)):
            # Allows for the prior-file to be moved to the local directory (file-transfer mechanism)
            self._prior_file = os.path.basename(prior_file)
        elif prior_file in self.default_prior_files:
            self._prior_file = self.default_prior_files[prior_file]
            self.distance_marginalization_lookup_table = self.get_distance_file_lookup_table(
                prior_file
            )
        else:
            raise FileNotFoundError("No prior file {} available".format(prior_file))

        logger.info("Prior-file set to {}".format(self._prior_file))

    @property
    def distance_marginalization_lookup_table(self):
        return self._distance_marginalization_lookup_table

    @distance_marginalization_lookup_table.setter
    def distance_marginalization_lookup_table(
        self, distance_marginalization_lookup_table
    ):
        if distance_marginalization_lookup_table is None:
            if hasattr(self, "_distance_marginalization_lookup_table"):
                pass
            else:
                self._distance_marginalization_lookup_table = None
        else:
            if hasattr(self, "_distance_marginalization_lookup_table"):
                logger.info("Overwriting distance_marginalization_lookup_table")
            self._distance_marginalization_lookup_table = (
                distance_marginalization_lookup_table
            )

    @property
    def default_prior(self):
        return getattr(self, "_default_prior", None)

    @default_prior.setter
    def default_prior(self, default_prior):
        self._default_prior = default_prior

    @property
    def combined_default_prior_dicts(self):
        d = bilby.core.prior.__dict__.copy()
        d.update(bilby.gw.prior.__dict__)
        return d

    @property
    def priors(self):
        if getattr(self, "_priors", None) is not None:
            return self._priors

        if self.default_prior in self.combined_default_prior_dicts.keys():
            self._priors = self.combined_default_prior_dicts[self.default_prior](
                filename=self.prior_file
            )
        else:
            raise ValueError("Unable to set prior: default_prior unavailable")

        if self._priors.get("geocent_time", None) is None:
            try:
                logger.info(
                    "Setting geocent time prior using trigger-time={} and deltaT={}".format(
                        self.trigger_time, self.deltaT
                    )
                )
                self._priors["geocent_time"] = bilby.core.prior.Uniform(
                    minimum=self.trigger_time - self.deltaT / 2,
                    maximum=self.trigger_time + self.deltaT / 2,
                    name="geocent_time",
                    latex_label="$t_c$",
                    unit="$s$",
                )
            except (AttributeError, TypeError):
                logger.info("Unable to set geocent time prior")

        if self.calibration_model is not None:
            for det in self.detectors:
                if det in self.spline_calibration_envelope_dict:
                    logger.info(
                        "Creating calibration prior for {} from {}".format(
                            det, self.spline_calibration_envelope_dict[det]
                        )
                    )
                    self._priors.update(
                        bilby.gw.prior.CalibrationPriorDict.from_envelope_file(
                            self.spline_calibration_envelope_dict[det],
                            minimum_frequency=self.minimum_frequency_dict[det],
                            maximum_frequency=self.maximum_frequency_dict[det],
                            n_nodes=self.spline_calibration_nodes,
                            label=det,
                        )
                    )
                elif (
                    det in self.spline_calibration_amplitude_uncertainty_dict
                    and det in self.spline_calibration_phase_uncertainty_dict
                ):
                    logger.info(
                        "Creating calibration prior for {} from "
                        "provided constant uncertainty values.".format(det)
                    )
                    self._priors.update(
                        bilby.gw.prior.CalibrationPriorDict.constant_uncertainty_spline(
                            amplitude_sigma=self.spline_calibration_amplitude_uncertainty_dict[
                                det
                            ],
                            phase_sigma=self.spline_calibration_phase_uncertainty_dict[
                                det
                            ],
                            minimum_frequency=self.minimum_frequency_dict[det],
                            maximum_frequency=self.maximum_frequency_dict[det],
                            n_nodes=self.spline_calibration_nodes,
                            label=det,
                        )
                    )
                else:
                    logger.warning(f"No calibration information for {det}")
        return self._priors

    @property
    def calibration_model(self):
        return getattr(self, "_calibration_model", None)

    @calibration_model.setter
    def calibration_model(self, calibration_model):
        if calibration_model is not None:
            logger.info("Setting calibration_model={}".format(calibration_model))
            self._calibration_model = calibration_model
        else:
            logger.info(
                "No calibration_model model provided, calibration "
                "marginalization will not be used"
            )
            self._calibration_model = None
