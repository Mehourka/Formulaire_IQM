"""
***************************************************************************
*                                                                         *
*   This program is free software; you can redistribute it and/or modify  *
*   it under the terms of the GNU General Public License as published by  *
*   the Free Software Foundation; either version 2 of the License, or     *
*   (at your option) any later version.                                   *
*                                                                         *
***************************************************************************
"""

from qgis.PyQt.QtCore import QCoreApplication
from PyQt5.QtCore import QVariant
from qgis.core import (
    QgsField,
    QgsFeature,
    QgsFields,
    QgsProcessing,
    QgsFeatureSink,
    QgsProcessingException,
    QgsProcessingAlgorithm,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterFeatureSink,
)
from qgis import processing
from typing import Tuple


class IqmFormProcessingAlgorithm(QgsProcessingAlgorithm):
    """
    This is an example algorithm that takes a vector layer and
    creates a new identical one.

    It is meant to be used as an example of how to create your own
    algorithms and explain methods and variables used to do it. An
    algorithm like this will be available in all elements, and there
    is not need for additional work.

    All Processing algorithms should extend the QgsProcessingAlgorithm
    class.
    """

    # Constants used to refer to parameters and outputs. They will be
    # used when calling the algorithm from another algorithm, or when
    # calling from the QGIS console.

    INPUT = "INPUT"
    OUTPUT = "OUTPUT"

    def initAlgorithm(self, config=None):
        """
        Here we define the inputs and output of the algorithm, along
        with some other properties.
        """

        # We add the input vector features source. It can have any kind of
        # geometry.
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.INPUT,
                self.tr("Formulaire IQM (couche vectorielle)"),
                [QgsProcessing.TypeVectorAnyGeometry],
            )
        )

        # We add a feature sink in which to store our processed features (this
        # usually takes the form of a newly created vector layer when the
        # algorithm is run in QGIS).
        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT, self.tr("Couche vectorielle résultante")
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        """
        Here is where the processing itself takes place.
        """
        # Define field names
        NB_INDICES_FN = "nb_computed_indices"
        SCORE_IQM_FN = "iqm_score"
        ID_FN = "id"
        UUID_FN = "uuid"
        # Retrieve the feature source and sink. The 'dest_id' variable is used
        # to uniquely identify the feature sink, and must be included in the
        # dictionary returned by the processAlgorithm function.
        source = self.parameterAsSource(parameters, self.INPUT, context)

        # If source was not found, throw an exception to indicate that the algorithm
        # encountered a fatal error. The exception text can be any string, but in this
        # case we use the pre-built invalidSourceError method to return a standard
        # helper text for when a source cannot be evaluated
        if source is None:
            raise QgsProcessingException(
                self.invalidSourceError(parameters, self.INPUT)
            )

        # Create the sink fields
        # sink_fields = source.fields()
        # if NB_INDICES_FN not in sink_fields.names():
        #     sink_fields.append(QgsField(NB_INDICES_FN, QVariant.Int))
        # if SCORE_IQM_FN not in sink_fields.names():
        #     sink_fields.append(QgsField(SCORE_IQM_FN, QVariant.Double))

        sink_fields = QgsFields()
        sink_fields.append(QgsField(ID_FN, QVariant.Int))
        sink_fields.append(QgsField(UUID_FN, QVariant.String))
        sink_fields.append(QgsField(NB_INDICES_FN, QVariant.Int))
        sink_fields.append(QgsField(SCORE_IQM_FN, QVariant.Double))

        (sink, dest_id) = self.parameterAsSink(
            parameters,
            self.OUTPUT,
            context,
            sink_fields,
            source.wkbType(),
            source.sourceCrs(),
        )

        if context.willLoadLayerOnCompletion(dest_id):
            layer_details = context.layerToLoadOnCompletionDetails(dest_id)
            layer_details.name = self.tr(f"couche_résultante_IQM")

        # Send some information to the user
        feedback.pushInfo("CRS is {}".format(source.sourceCrs().authid()))

        # If sink was not created, throw an exception to indicate that the algorithm
        # encountered a fatal error. The exception text can be any string, but in this
        # case we use the pre-built invalidSinkError method to return a standard
        # helper text for when a sink cannot be evaluated
        if sink is None:
            raise QgsProcessingException(self.invalidSinkError(parameters, self.OUTPUT))

        # Compute the number of steps to display within the progress bar and
        # get features from source
        total = 100.0 / source.featureCount() if source.featureCount() else 0
        features = source.getFeatures()

        for current, feature in enumerate(features):
            # Stop the algorithm if cancel button has been clicked
            if feedback.isCanceled():
                break

            new_feature = QgsFeature(sink_fields)
            new_feature.setGeometry(feature.geometry())
            new_feature[ID_FN] = feature.id()
            if UUID_FN in feature.fields().names():
                new_feature[UUID_FN] = feature.attribute(UUID_FN)

            # Compute the IQM
            indices_count, iqm_score = compute_form_iqm(feature)

            # Add a new attribute to the feature
            new_feature[NB_INDICES_FN] = indices_count
            new_feature[SCORE_IQM_FN] = round(iqm_score, 3)

            # Add a feature in the sink
            sink.addFeature(new_feature, QgsFeatureSink.FastInsert)

            # Update the progress bar
            feedback.setProgress(int(current * total))

        return {self.OUTPUT: dest_id}

    def tr(self, string):
        """
        Returns a translatable string with the self.tr() function.
        """
        return QCoreApplication.translate("Processing", string)

    def createInstance(self):
        return IqmFormProcessingAlgorithm()

    def name(self):
        """
        Returns the algorithm name, used for identifying the algorithm. This
        string should be fixed for the algorithm, and must not be localised.
        The name should be unique within each provider. Names should contain
        lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return "computeformiqm"

    def displayName(self):
        """
        Returns the translated algorithm name, which should be used for any
        user-visible display of the algorithm name.
        """
        return self.tr("Calcul Formulaire IQM")

    def group(self):
        """
        Returns the name of the group this algorithm belongs to. This string
        should be localised.
        """
        return self.tr("Formulaire IQM")

    def groupId(self):
        """
        Returns the unique ID of the group this algorithm belongs to. This
        string should be fixed for the algorithm, and must not be localised.
        The group id should be unique within each provider. Group id should
        contain lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return "formiqm"

    def shortHelpString(self):
        """
        Returns a localised short helper string for the algorithm. This string
        should provide a basic description about what the algorithm does and the
        parameters and outputs associated with it..
        """
        return self.tr(
            "Calcul de l'Indice de Qualité Morphologique (IQM) à partir d'un formulaire de relevé de terrain."
        )
from typing import Tuple


def interpolate_value(x_values, y_values, value):
    """
    Interpolates a value given a dynamic number of x, y values.

    Parameters:
    x_values (list or array-like): List of x values.
    y_values (list or array-like): List of y values.
    value (float): The value to interpolate.

    Returns:
    float: The interpolated value.
    """
    # Find the two closest x values
    left_index = 0
    right_index = len(x_values) - 1
    while right_index - left_index > 1:
        mid_index = (left_index + right_index) // 2
        if x_values[mid_index] <= value:
            left_index = mid_index
        else:
            right_index = mid_index

    # Perform linear interpolation
    x_left = x_values[left_index]
    x_right = x_values[right_index]
    y_left = y_values[left_index]
    y_right = y_values[right_index]
    if left_index > 0:
        y_left = (y_left + y_values[left_index - 1]) / 2
    if right_index < len(y_values) - 1:
        y_right = (y_right + y_left) / 2
    interpolated_value = y_left + (value - x_left) * (y_right - y_left) / (
        x_right - x_left
    )
    return min(max(interpolated_value, y_values[0]), y_values[-1])


def calcul_A1(score: float) -> Tuple[float, int]:
    MAX_SCORE = 6

    if isinstance(score, (int, float)):
        return (score, MAX_SCORE)
    return (0, 0)


def calcul_A2(
    aire_drain: float,
    aire_drain_struct: float,
    struct_type: str,
    f_t1_amont: bool,
    score=None,
) -> Tuple[float, int]:
    """
    Parameters:
    aire_drain (float): Aire de drainage du tronçon.
    aire_drain_struct (float): Aire de dracinage de la strcture.
    t1_en_amont (bool): True si presence d'un barrage (T1) a l'extremité amont.
    type_int (int): type de structure (0: 'T1', 1: 'T2', 2: 'T3').

    Returns:
    Tuple[score, MAX_SCORE]
    En cas d'echec, returns tuple (0,0)
    """
    MAX_SCORE = 12
    if isinstance(score, (int, float)):
        return (score, MAX_SCORE)

    parameters = [aire_drain, aire_drain_struct, f_t1_amont]
    if None in parameters:
        return (0, 0)

    if not struct_type:
        return (0, MAX_SCORE)

    aire_relative = aire_drain_struct / aire_drain

    if not (0 <= aire_relative <= 1):
        return (0, 0)

    if struct_type.lower() not in ["t1", "t2", "t3"]:
        return (0, 0)

    struct_type = struct_type.upper()

    if f_t1_amont is True and struct_type == "T1":
        return (12, MAX_SCORE)

    if struct_type == "T1":
        x_val = [0, 0.05, 0.33, 0.66]
        y_val = [0, 3, 6, 9]
    if struct_type == "T2":
        x_val = [0, 0.33, 0.66]
        y_val = [0, 3, 6]
    else:  # (struct_type == "T3"):
        x_val = [0, 0.66]
        y_val = [0, 3]

    score = interpolate_value(x_val, y_val, aire_relative)
    return (score, MAX_SCORE)


def calcul_A3(
    score: float,
) -> Tuple[float, int]:
    """
    Parameters:
    score: reponse directe du formulaire

    Returns:
    Tuple[score, MAX_SCORE]
    En cas d'echec, returns tuple (0,0)
    """
    MAX_SCORE = 6
    # Check that no parameter is None
    if isinstance(score, (int, float)):
        return (score, MAX_SCORE)
    return (0, 0)


def calcul_A4(
    nb_structs: float, long_seg_m: float, f_t1_aval: bool, score=None
) -> Tuple[float, int]:
    """
    Calculates the A4 value based on the number of structures
    and the length of the segment.

    Parameters:
    nb_structs (float): The number of structures.
    long_seg_m (float): The length of the segment in meters.

    Returns:
    Tuple[float, int]: A tuple containing the calculated A4 value
    and the maximum score.
    """
    MAX_SCORE = 6
    if isinstance(score, (int, float)):
        return (score, MAX_SCORE)

    parameters = [nb_structs, long_seg_m, f_t1_aval]
    if None in parameters or long_seg_m <= 0:
        return (0, 0)

    density_km = (nb_structs / long_seg_m) * 1000
    if f_t1_aval is True:
        x_val = [1, 4 / 3, 2]
        y_val = [6, 12, 18]
    else:
        x_val = [0, 1, 4 / 3, 2]
        y_val = [0, 6, 12, 18]

    score = interpolate_value(x_val, y_val, density_km)
    return (score, MAX_SCORE)


def calcul_A5(
    nb_trav: float,
    long_seg_m: float,
    score=None,
) -> Tuple[float, int]:
    """
    Calculates the A5 value based on the number of structures
    and the length of the segment.

    Parameters:
    nb_trav (float): The number of structures.
    long_seg_m (float): The length of the segment in meters.

    Returns:
    Tuple[float, int]: A tuple containing the calculated A4 value
    and the maximum score.
    """
    MAX_SCORE = 3
    if isinstance(score, (int, float)):
        return (score, MAX_SCORE)

    # Check parameters validity
    parameters = [nb_trav, long_seg_m]
    if None in parameters or long_seg_m <= 0:
        return (0, 0)

    density_km = (nb_trav / long_seg_m) * 1000

    x_val = [0, 3]
    y_val = [0, 1]
    score = interpolate_value(x_val, y_val, density_km)
    return (score, MAX_SCORE)


def calcul_A6(
    long_protection_metre: float,
    long_seg_m: float,
    score=None,
) -> Tuple[float, int]:
    MAX_SCORE = 6
    if isinstance(score, (int, float)):
        return (score, MAX_SCORE)

    # Check parameters validity
    parameters = [long_protection_metre, long_seg_m]
    if None in parameters or long_seg_m <= 0:
        return (0, 0)

    ratio = long_protection_metre / (long_seg_m * 2)

    x_val = [5, 33, 50, 80]
    y_val = [0, 6, 12, 18]
    score = interpolate_value(x_val, y_val, ratio * 100)
    return (score, MAX_SCORE)


def calcul_A7(
    long_digues_m: float,
    long_seg_m: float,
    f_en_retrait: bool,
    score=None,
) -> Tuple[float, int]:
    MAX_SCORE = 6
    if isinstance(score, (int, float)):
        return (score, MAX_SCORE)

    # Check parameters validity
    parameters = [long_digues_m, long_seg_m, f_en_retrait]
    if None in parameters or long_seg_m <= 0:
        return (0, 0)

    if f_en_retrait is True:
        return (0, MAX_SCORE)

    ratio = long_digues_m / (long_seg_m * 2)

    x_val = [0, 5, 50, 66, 80]
    y_val = [0, 3, 6, 12, 18]
    score = interpolate_value(x_val, y_val, ratio * 100)
    return (score, MAX_SCORE)


def calcul_A8(
    long_modif_m: float,
    long_seg_m: float,
    score_f2: float,
    score=None,
) -> Tuple[float, int]:
    MAX_SCORE = 3
    if isinstance(score, (int, float)):
        return (score, MAX_SCORE)

    # Check parameters validity
    parameters = [long_modif_m, long_seg_m, score_f2]
    if None in parameters or long_seg_m <= 0:
        return (0, 0)

    ratio = long_modif_m / (long_seg_m)

    x_val = [0, 10, 50, 80, 100]
    y_val = [0, 2, 3, 9, 15]

    if score_f2 < 2:
        x_val = [0, 50, 80, 100]
        y_val = [0, 3, 9, 15]
    if 2 <= score_f2 <= 3:
        x_val = [0, 10, 80, 100]
        y_val = [0, 2, 3, 15]

    score = interpolate_value(x_val, y_val, ratio * 100)
    return (score, MAX_SCORE)


def calcul_A9(
    long_revetement_m: float,
    long_seg_m: float,
    score=None,
) -> Tuple[float, int]:
    MAX_SCORE = 8

    if isinstance(score, (int, float)):
        return (score, MAX_SCORE)

    # Check parameters validity
    parameters = [long_revetement_m, long_seg_m]

    if None in parameters or long_seg_m <= 0:
        return (0, 0)

    ratio = long_revetement_m / (long_seg_m)

    x_val = [0, 5, 15, 33, 50, 80]
    y_val = [0, 3, 6, 8, 14, 20]
    score = interpolate_value(x_val, y_val, ratio * 100)
    return (score, MAX_SCORE)


def calcul_A10(score: float) -> Tuple[float, int]:
    MAX_SCORE = 6

    if isinstance(score, (int, float)):
        return (score, MAX_SCORE)
    return (0, 0)


def calcul_A11(score: float) -> Tuple[float, int]:
    MAX_SCORE = 5

    if isinstance(score, (int, float)):
        return (score, MAX_SCORE)
    return (0, 0)


def calcul_A12(score: float) -> Tuple[float, int]:
    MAX_SCORE = 5

    if isinstance(score, (int, float)):
        return (score, MAX_SCORE)
    return (0, 0)


def calcul_CA1(score: float, f_confine: bool) -> Tuple[float, int]:
    if f_confine:
        MAX_SCORE = 3
    else:
        MAX_SCORE = 6

    if isinstance(score, (int, float)):
        return (score, MAX_SCORE)
    return (0, 0)


def calcul_CA2(score: float, f_confine: bool) -> Tuple[float, int]:
    if f_confine:
        MAX_SCORE = 3
    else:
        MAX_SCORE = 6

    if isinstance(score, (int, float)):
        return (score, MAX_SCORE)
    return (0, 0)


def calcul_CA3(score: float, f_confine: bool) -> Tuple[float, int]:
    if f_confine:
        MAX_SCORE = 8
    else:
        MAX_SCORE = 12

    if isinstance(score, (int, float)):
        return (score, MAX_SCORE)
    return (0, 0)


def compute_indic_A(attr_dict):
    results = {}

    # General
    long_seg_m = attr_dict.get("longueur_seg_m")
    f_confine = attr_dict.get("glob_class_conf") == 1


    # A1
    val = attr_dict.get("A1_vmap")
    results["A1"] = calcul_A1(val)

    # A2
    aire_drain = attr_dict.get("A2_aire_drainage_km2")
    aire_drain_struct = attr_dict.get("A2_aire_drainage_struct_km2")
    type_struct = attr_dict.get("A2_type_struct")
    t1_limit = attr_dict.get("A2_f_t1_limit")
    results["A2"] = calcul_A2(
        aire_drain,
        aire_drain_struct,
        type_struct,
        t1_limit,
        score=attr_dict.get("A2_vmap"),
    )

    # A3
    val = attr_dict.get("A3_vmap")
    results["A3"] = calcul_A3(val)

    # A4
    nbr_structs = attr_dict.get("A4_nbr_structs")
    f_t1_aval = attr_dict.get("A4_f_t1_aval")
    results["A4"] = calcul_A4(
        nbr_structs,
        long_seg_m,
        f_t1_aval,
        score=attr_dict.get("A4_vmap"),
    )

    # A5
    nbr_traverses = attr_dict.get("A5_nbr_traverses")
    results["A5"] = calcul_A5(nbr_traverses, long_seg_m, score=attr_dict.get("A5_vmap"))

    # A6
    long_prot_m = attr_dict.get("A6_long_protection_m")
    results["A6"] = calcul_A6(long_prot_m, long_seg_m, score=attr_dict.get("A6_vmap"))

    # A7
    long_digues_m = attr_dict.get("A7_longueur_digues_m")
    f_en_retrait = attr_dict.get("A7_en_retrait")
    results["A7"] = calcul_A7(
        long_digues_m, long_seg_m, f_en_retrait, score=attr_dict.get("A7_vmap")
    )

    # A8
    long_modif_m = attr_dict.get("A8_long_modif_m")
    score_f2 = attr_dict.get("F2_score")
    results["A8"] = calcul_A8(
        long_modif_m, long_seg_m, score_f2, score=attr_dict.get("A8_vmap")
    )

    # A9
    long_revetement_m = attr_dict.get("A9_long_revetement_m")
    results["A9"] = calcul_A9(
        long_revetement_m, long_seg_m, score=attr_dict.get("A9_vmap")
    )

    # A10
    val = attr_dict.get("A10_vmap")
    results["A10"] = calcul_A10(val)

    # A11
    val = attr_dict.get("A11_vmap")
    results["A11"] = calcul_A11(val)

    # A12
    val = attr_dict.get("A12_vmap")
    results["A12"] = calcul_A12(val)

    # CA1
    val = attr_dict.get("CA1_vmap")
    results["CA1"] = calcul_CA1(val, f_confine)

    # CA2
    val = attr_dict.get("CA2_vmap")
    results["CA2"] = calcul_CA2(val, f_confine)

    # CA3
    val = attr_dict.get("CA3_vmap")
    results["CA3"] = calcul_CA3(val, f_confine)

    return results


def calcul_F1(score: float) -> Tuple[float, int]:
    MAX_SCORE = 5

    if isinstance(score, (int, float)):
        return (score, MAX_SCORE)
    return (0, 0)


def bool_larg_suffisante(
	larg_chenal_m: float,
	larg_cible_m: float,
	style_fluvial: int,
) -> bool:

	params = [larg_chenal_m, larg_cible_m, style_fluvial]
	if None in params:
		return None
	# Largeur suffisante
	thresh = 2
	if style_fluvial >= 4 and style_fluvial <= 5:
		thresh = 1

	if larg_cible_m >= thresh * larg_chenal_m:
		return True
	return False


def calcul_F2(
    long_pl_alluv_m: float,
    long_seg_m: float,
    f_larg_suffisante: bool,
    score=None,
) -> Tuple[float, int]:
    MAX_SCORE = 5
    if isinstance(score, (int, float)):
        return (score, MAX_SCORE)

    # Check parameters validity
    parameters = [long_pl_alluv_m, long_seg_m, f_larg_suffisante]

    if None in parameters or long_seg_m <= 0:
        return (0, 0)

    ratio = long_pl_alluv_m / (long_seg_m)

    x_val = [100, 66, 10]
    y_val = [0, 2, 5]
    score = interpolate_value(x_val, y_val, ratio * 100)
    if 2 <= score <= 5 and not f_larg_suffisante:
        score += 1
    return (score, MAX_SCORE)


def calcul_F3(
    sup_connect: float,
    long_seg_m: float,
    score=None,
) -> Tuple[float, int]:
    MAX_SCORE = 5
    if isinstance(score, (int, float)):
        return (score, MAX_SCORE)

    # Check parameters validity
    parameters = [sup_connect, long_seg_m]

    if None in parameters or long_seg_m <= 0:
        return (0, 0)

    ratio = sup_connect / (long_seg_m * 2 * 50)
    x_val = [90, 33, 0]
    y_val = [0, 3, 5]
    score = interpolate_value(x_val, y_val, ratio * 100)
    return (score, MAX_SCORE)


def calcul_F4(score: float) -> Tuple[float, int]:
    MAX_SCORE = 3

    if isinstance(score, (int, float)):
        return (score, MAX_SCORE)
    return (0, 0)


def calcul_F5(
    long_cep_m: float,
    long_seg_m: float,
    f_larg_suffisante: bool,
    score=None,
) -> Tuple[float, int]:
    MAX_SCORE = 3
    if isinstance(score, (int, float)):
        return (score, MAX_SCORE)

    # Check parameters validity
    parameters = [long_cep_m, long_seg_m, f_larg_suffisante]

    if None in parameters or long_seg_m <= 0:
        return (0, 0)

    ratio = long_cep_m / (long_seg_m)

    x_val = [100, 66, 33]
    y_val = [0, 2, 3]
    score = interpolate_value(x_val, y_val, ratio * 100)
    if 0 == score and not f_larg_suffisante:
        score = 2
    return (score, MAX_SCORE)


def calcul_F6(
    long_coherente_m: float,
    long_seg_m: float,
    score=None,
) -> Tuple[float, int]:
    MAX_SCORE = 3
    if isinstance(score, (int, float)):
        return (score, MAX_SCORE)

    # Check parameters validity
    parameters = [long_coherente_m, long_seg_m]

    if None in parameters or long_seg_m <= 0:
        return (0, 0)

    ratio = long_coherente_m / (long_seg_m)
    x_val = [66, 33]
    y_val = [0, 3]
    score = interpolate_value(x_val, y_val, ratio * 100)
    return (score, MAX_SCORE)


def calcul_F7(
    long_alter_m: float,
    long_seg_m: float,
    score=None,
) -> Tuple[float, int]:
    MAX_SCORE = 5
    if isinstance(score, (int, float)):
        return (score, MAX_SCORE)

    # Check parameters validity
    parameters = [long_alter_m, long_seg_m]

    if None in parameters or long_seg_m <= 0:
        return (0, 0)

    ratio = long_alter_m / (long_seg_m)
    x_val = [5, 33, 66]
    y_val = [0, 3, 5]
    score = interpolate_value(x_val, y_val, ratio * 100)
    return (score, MAX_SCORE)


def calcul_F8(score: float) -> Tuple[float, int]:
    MAX_SCORE = 3

    if isinstance(score, (int, float)):
        return (score, MAX_SCORE)
    return (0, 0)


def calcul_F9(
    long_alter_m: float,
    long_seg_m: float,
    score=None,
) -> Tuple[float, int]:
    MAX_SCORE = 5
    if isinstance(score, (int, float)):
        return (score, MAX_SCORE)

    # Check parameters validity
    parameters = [long_alter_m, long_seg_m]

    if None in parameters or long_seg_m <= 0:
        return (0, 0)

    ratio = long_alter_m / (long_seg_m)
    x_val = [5, 33]
    y_val = [0, 5]
    score = interpolate_value(x_val, y_val, ratio * 100)
    return (score, MAX_SCORE)


def calcul_F10(score: float) -> Tuple[float, int]:
    MAX_SCORE = 6
    if isinstance(score, (int, float)):
        return (score, MAX_SCORE)
    return (0, 0)


def calcul_F11(score: float) -> Tuple[float, int]:
    MAX_SCORE = 3

    if isinstance(score, (int, float)):
        return (score, MAX_SCORE)
    return (0, 0)


def calcul_F12(
    long_seg_m: float,
    larg_chenal_m: float,
    aire_vege_fonc_m2: float,
    style_fluvial: int,
    f_confine: bool,
    score = None,
) -> Tuple[float, int]:
    MAX_SCORE = 3

    if isinstance(score, (int, float)):
        return (score, MAX_SCORE)

    parameters = [long_seg_m, aire_vege_fonc_m2, f_confine, larg_chenal_m, style_fluvial]
    if None in parameters or long_seg_m <= 0:
        return (0, 0)

    aire = 0
    if f_confine:
        aire = (50 * 2 * long_seg_m)
        x_val = [90, 33, 0]
    else :
        aire = larg_chenal_m * long_seg_m
        if aire == 0:
            return (0, 0)
        if style_fluvial < 4 or style_fluvial > 5:
            x_val = [100, 50, 0]
        else:
            x_val = [200, 50, 0]

    ratio = aire_vege_fonc_m2 / aire * 100

    y_val = [3, 2, 0]
    score = interpolate_value(x_val, y_val, ratio)
    if isinstance(score, (int, float)):
        return (score, MAX_SCORE)
    return (0, 0)


def calcul_F13(
    long_seg_m: float,
    long_vege_fonc_m: float,
    score=None,
) -> Tuple[float, int]:
    MAX_SCORE = 5

    if isinstance(score, (int, float)):
        return (score, MAX_SCORE)

    prams = [long_seg_m, long_vege_fonc_m]
    if None in prams or long_seg_m <= 0:
        return (0, 0)

    ratio = long_alter_m / (long_seg_m)
    x_val = [90, 33, 0]
    y_val = [0, 3, 5]
    score = interpolate_value(x_val, y_val, ratio * 100)
    return (0, 0)


def compute_indic_F(attr_dict):
    results = {}

    # General
    long_seg_m = attr_dict.get("longueur_seg_m")
    larg_chenal_m = attr_dict.get("glob_larg_chenal_m")
    style_fluv = attr_dict.get("glob_style_fluv")
    f_confine = attr_dict.get("glob_class_conf") == 1

    # F1
    val = attr_dict.get("F1_vmap")
    results["F1"] = calcul_F1(val)

    # F2
    long_pl_alluv_m = attr_dict.get("F2_long_pl_alluv_m")
    larg_pl_alluv_m = attr_dict.get("F2_larg_pl_alluv_m")
    f_larg_suffisante = bool_larg_suffisante(larg_chenal_m, larg_pl_alluv_m, style_fluv)
    results["F2"] = calcul_F2(
        long_pl_alluv_m, long_seg_m, f_larg_suffisante, score=attr_dict.get("F2_vmap")
    )

    # F3
    aire_connecte_m2 = attr_dict.get("F3_aire_connecte_m2")
    results["F3"] = calcul_F3(
        aire_connecte_m2, long_seg_m, score=attr_dict.get("F3_vmap")
    )

    # F4
    val = attr_dict.get("F4_vmap")
    results["F4"] = calcul_F4(val)

    # F5
    long_cep_m = attr_dict.get("F5_long_cep_m")
    larg_cep_m = attr_dict.get("F5_larg_cep_m")
    f_larg_suffisante = bool_larg_suffisante(larg_chenal_m, larg_cep_m, style_fluv)
    results["F5"] = calcul_F5(
        long_cep_m, long_seg_m, f_larg_suffisante, score=attr_dict.get("F5_vmap")
    )

    # F6
    long_coherente_m = attr_dict.get("F6_long_coherente_m")
    results["F6"] = calcul_F6(
        long_coherente_m, long_seg_m, score=attr_dict.get("F6_vmap")
    )

    # F7
    long_alter_m = attr_dict.get("F7_long_alter_m")
    results["F7"] = calcul_F7(long_alter_m, long_seg_m, score=attr_dict.get("F7_vmap"))

    # F8
    val = attr_dict.get("F8_vmap")
    results["F8"] = calcul_F8(val)

    # F9
    long_alter_m = attr_dict.get("F9_long_alter_m")
    results["F9"] = calcul_F9(long_alter_m, long_seg_m, score=attr_dict.get("F9_vmap"))

    # F10
    val = attr_dict.get("F10_vmap")
    results["F10"] = calcul_F10(val)

    # F11
    val = attr_dict.get("F11_vmap")
    results["F11"] = calcul_F11(val)

    # F12
    aire_vege_fonc_m2 = attr_dict.get("F12_aire_vege_fonctionelle_m2")
    results["F12"] = calcul_F12(
        long_seg_m,
        larg_chenal_m,
        aire_vege_fonc_m2,
        style_fluv,
        f_confine,
        score=attr_dict.get("F12_vmap")
    )

    # F13
    long_vege_fonc_m = attr_dict.get("F13_long_vege_fonc_m")

    results["F13"] = calcul_F13(
        long_seg_m,
        long_vege_fonc_m,
        score=attr_dict.get("F13_vmap"),
    )
    return results


def attr_to_dict(feature):
    attr_names = [field.name() for field in feature.fields()]
    attrs = feature.attributes()
    attr_dict = dict(zip(attr_names, attrs))
    return attr_dict


def compute_form_iqm(feature):
    results = {}

    attr_dict = attr_to_dict(feature)

    results.update(compute_indic_F(attr_dict))
    attr_dict["F2_score"] = results["F2"][0] if results["F2"][1] > 0 else -1

    results.update(compute_indic_A(attr_dict))

    max_score = sum(elem[1] for elem in results.values())
    indices_count = sum(elem[1] != 0 for elem in results.values())
    if max_score == 0:
        return (0, -1)
    total_score = sum(elem[0] for elem in results.values())
    iqm = 1 - total_score / max_score
    return indices_count, iqm


