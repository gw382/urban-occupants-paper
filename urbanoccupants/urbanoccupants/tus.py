"""Functions and mapping for the UK Time Use Study 2000 data.

The mappings bring the data into categories that are used in this study. Typically
that means the number of categories is reduces vastly.
"""
from enum import Enum

import numpy as np
import pandas as pd

from pytus2000 import diary, individual, household
from .person import WeekMarkovChain
from .types import EconomicActivity, Qualification, HouseholdType, AgeStructure, Pseudo, Carer,\
    PersonalIncome, PopulationDensity, Region, DwellingType


def filter_features_and_drop_nan(seed, features):
    """Filters seed by chosen features and drops nans.

    If there is any nan in any chosen feature for a certain individual in the seed, that
    individual will be dropped.
    """
    if isinstance(features, tuple): # 2D
        features = list(features)
    filtered_seed = seed[features].dropna(axis='index', how='any')
    assert filtered_seed.shape[0] > 0, 'Seed filtered by features {} is empty.'.format(features)
    return filtered_seed


def filter_features(seed, markov_ts, features):
    """Filters data sets for features and drops all missing values.

    This will:
        * filter features in the seed
        * drop all individuals in seed for which at least one feature is missing
        * drop all diaries in the markov_ts whose individuals are not in seed
        * drop all individuals from seed which are not in the markov_ts

    Returns:
        * (seed, markov_ts) as tuple
    """
    seed = filter_features_and_drop_nan(seed, [str(feature) for feature in features])
    markov_ts = markov_ts[markov_ts.index.droplevel(['daytype', 'time_of_day']).isin(seed.index)]
    seed = seed[seed.index.isin(markov_ts.index.droplevel(['daytype', 'time_of_day']))]
    return seed, markov_ts


def markov_chain_for_cluster(param_tuple):
    """Creating a heterogenous markov chain for a cluster of the TUS sample.

    This function is intended to be used with `multiprocessing.imap_unordered` which allows
    only one parameter, hence the inconvenient tuple parameter design.

    Parameters:
        * param_tuple(0): time series for all people, with index (SN1, SN2, SN3, daytype, timeofday)
        * param_tuple(1): a subset of the individual data set representing the cluster for which
                          the markov chain should be created, with index (SN1, SN2, SN3)
        * param_tuple(2): the tuple of people features representing the cluster, this is not used
                          in this function, but only passed through
        * param_tuple(3): the time step size of the markov chain, a datetime.timedelta object

    Returns:
        a tuple of
            * param_tuple(2)
            * the heterogeneous markov chain for the cluster
    """
    markov_ts, group_of_people, features, time_step_size = param_tuple
    # filter by people
    people_mask = markov_ts.index.droplevel([3, 4]).isin(group_of_people.index)
    filtered_markov = pd.DataFrame(markov_ts)[people_mask].sort_index()
    # filter by weekday
    idx = pd.IndexSlice
    filtered_markov_weekday = filtered_markov.loc[idx[:, :, :, 'weekday'], :]
    # filter by weekend
    filtered_markov_weekend = filtered_markov.loc[idx[:, :, :, 'weekend'], :]
    return features, WeekMarkovChain(
        weekday_time_series=filtered_markov_weekday.unstack(level=[0, 1, 2, 3]),
        weekend_time_series=filtered_markov_weekend.unstack(level=[0, 1, 2, 3]),
        time_step_size=time_step_size
    )


class Location(Enum):
    """Simplified TUS 2000 locations."""
    HOME = 1
    OTHER_HOME = 2
    WORK_OR_SCHOOL = 3
    RESTO = 4
    SPORTS_FACILITY = 5
    ARTS_OR_CULTURAL_CENTRE = 6
    OUTSIDE = 7
    TRAVELLING = 8
    IMPLICIT = 9


class Activity(Enum):
    """Simplified TUS 2000 activities."""
    SLEEP = 1
    WORK_OR_STUDY = 2
    OTHER = 3


LOCATION_MAP = {
    diary.WHER_001.MAIN_ACTVTY_EQUAL_SLEEPWORKSTUDY___NO_CODE_REQUIRED: Location.IMPLICIT,
    diary.WHER_001._MISSING: np.nan,
    diary.WHER_001.MISSING2: np.nan,
    diary.WHER_001._UNSPECIFIED_LOCATION: np.nan,
    diary.WHER_001._UNSPECIFIED_LOCATION_NOT_TRAVELLING: np.nan,
    diary.WHER_001._HOME: Location.HOME,
    diary.WHER_001._SECOND_HOME_OR_WEEKEND_HOUSE: Location.OTHER_HOME,
    diary.WHER_001._WORKING_PLACE_OR_SCHOOL: Location.WORK_OR_SCHOOL,
    diary.WHER_001._OTHER_PEOPLE_S_HOME: Location.OTHER_HOME,
    diary.WHER_001._RESTAURANT__CAFÉ_OR_PUB: Location.RESTO,
    diary.WHER_001._SPORTS_FACILITY: Location.SPORTS_FACILITY,
    diary.WHER_001._WHER_001__ARTS_OR_CULTURAL_CENTRE: Location.ARTS_OR_CULTURAL_CENTRE,
    diary.WHER_001._THE_COUNTRY_COUNTRYSIDE__SEASIDE__BEACH_OR_COAST: Location.OUTSIDE,
    diary.WHER_001._OTHER_SPECIFIED_LOCATION_NOT_TRAVELLING: np.nan,
    diary.WHER_001._UNSPECIFIED_PRIVATE_TRANSPORT_MODE: Location.TRAVELLING,
    diary.WHER_001._TRAVELLING_ON_FOOT: Location.TRAVELLING,
    diary.WHER_001._TRAVELLING_BY_BICYCLE: Location.TRAVELLING,
    diary.WHER_001._TRAVELLING_BY_MOPED__MOTORCYCLE_OR_MOTORBOAT: Location.TRAVELLING,
    diary.WHER_001._TRAVELLING_BY_PASSENGER_CAR_AS_THE_DRIVER: Location.TRAVELLING,
    diary.WHER_001._TRAVELLING_BY_PASSENGER_CAR_AS_A_PASSENGER: Location.TRAVELLING,
    diary.WHER_001._TRAVELLING_BY_PASSENGER_CAR_DRIVER_STATUS_UNSPECIFIED: Location.TRAVELLING,
    diary.WHER_001._TRAVELLING_BY_LORRY__OR_TRACTOR: Location.TRAVELLING,
    diary.WHER_001._TRAVELLING_BY_VAN: Location.TRAVELLING,
    diary.WHER_001._OTHER_SPECIFIED_PRIVATE_TRAVELLING_MODE: Location.TRAVELLING,
    diary.WHER_001._UNSPECIFIED_PUBLIC_TRANSPORT_MODE: Location.TRAVELLING,
    diary.WHER_001._TRAVELLING_BY_TAXI: Location.TRAVELLING,
    diary.WHER_001._TRAVELLING_BY_BUS: Location.TRAVELLING,
    diary.WHER_001._TRAVELLING_BY_TRAM_OR_UNDERGROUND: Location.TRAVELLING,
    diary.WHER_001._TRAVELLING_BY_TRAIN: Location.TRAVELLING,
    diary.WHER_001._TRAVELLING_BY_AEROPLANE: Location.TRAVELLING,
    diary.WHER_001._TRAVELLING_BY_BOAT_OR_SHIP: Location.TRAVELLING,
    diary.WHER_001._WHER_001__TRAVELLING_BY_COACH: Location.TRAVELLING,
    diary.WHER_001._WAITING_FOR_PUBLIC_TRANSPORT: Location.TRAVELLING,
    diary.WHER_001._OTHER_SPECIFIED_PUBLIC_TRANSPORT_MODE: Location.TRAVELLING,
    diary.WHER_001._UNSPECIFIED_TRANSPORT_MODE: Location.TRAVELLING,
    diary.WHER_001._ILLEGIBLE_LOCATION_OR_TRANSPORT_MODE: np.nan
}


ACTIVITY_MAP = {
    diary.ACT1_001.UNSPECIFIED_PERSONAL_CARE: Activity.OTHER,
    diary.ACT1_001.UNSPECIFIED_SLEEP: Activity.SLEEP,
    diary.ACT1_001.SLEEP: Activity.SLEEP,
    diary.ACT1_001.SICK_IN_BED: Activity.SLEEP,
    diary.ACT1_001.EATING: Activity.OTHER,
    diary.ACT1_001.UNSPECIFIED_OTHER_PERSONAL_CARE: Activity.OTHER,
    diary.ACT1_001.WASH_AND_DRESS: Activity.OTHER,
    diary.ACT1_001.OTHER_SPECIFIED_PERSONAL_CARE: Activity.OTHER,
    diary.ACT1_001.UNSPECIFIED_EMPLOYMENT: Activity.WORK_OR_STUDY,
    diary.ACT1_001.WORKING_TIME_IN_MAIN_JOB: Activity.WORK_OR_STUDY,
    diary.ACT1_001.COFFEE_AND_OTHER_BREAKS_IN_MAIN_JOB: Activity.OTHER,
    diary.ACT1_001.WORKING_TIME_IN_SECOND_JOB: Activity.WORK_OR_STUDY,
    diary.ACT1_001.COFFEE_AND_OTHER_BREAKS_IN_SECOND_JOB: Activity.OTHER,
    diary.ACT1_001.UNSPECIFIED_ACTIVITIES_RELATED_TO_EMPLOYMENT: Activity.WORK_OR_STUDY,
    diary.ACT1_001.LUNCH_BREAK: Activity.OTHER,
    diary.ACT1_001.OTHER_SPECIFIED_ACTIVITIES_RELATED_TO_EMPLOYMENT: Activity.WORK_OR_STUDY,
    diary.ACT1_001.ACTIVITIES_RELATED_TO_JOB_SEEKING: Activity.OTHER,
    diary.ACT1_001.OTHER_SPECIFIED_ACTIVITIES_RELATED_TO_EMPLOYMENT2: Activity.WORK_OR_STUDY,
    diary.ACT1_001.UNSPECIFIED_STUDY: Activity.WORK_OR_STUDY,
    diary.ACT1_001.UNSPECIFIED_ACTIVITIES_RELATED_TO_SCHOOL_OR_UNIVERSITY: Activity.WORK_OR_STUDY,
    diary.ACT1_001.CLASSES_AND_LECTURES: Activity.WORK_OR_STUDY,
    diary.ACT1_001.HOMEWORK: Activity.OTHER,
    diary.ACT1_001.OTHER_SPECIFIED_ACTIVITIES_RELATED_TO_SCHOOL_OR_UNIVERSITY:
        Activity.WORK_OR_STUDY,
    diary.ACT1_001.FREE_TIME_STUDY: Activity.OTHER,
    diary.ACT1_001.UNSPECIFIED_HOUSEHOLD_AND_FAMILY_CARE: Activity.OTHER,
    diary.ACT1_001.UNSPECIFIED_FOOD_MANAGEMENT: Activity.OTHER,
    diary.ACT1_001.FOOD_PREPARATION: Activity.OTHER,
    diary.ACT1_001.BAKING: Activity.OTHER,
    diary.ACT1_001.DISH_WASHING: Activity.OTHER,
    diary.ACT1_001.PRESERVING: Activity.OTHER,
    diary.ACT1_001.OTHER_SPECIFIED_FOOD_MANAGEMENT: Activity.OTHER,
    diary.ACT1_001.UNSPECIFIED_HOUSEHOLD_UPKEEP: Activity.OTHER,
    diary.ACT1_001.CLEANING_DWELLING: Activity.OTHER,
    diary.ACT1_001.CLEANING_YARD: Activity.OTHER,
    diary.ACT1_001.HEATING_AND_WATER: Activity.OTHER,
    diary.ACT1_001.VARIOUS_ARRANGEMENTS: Activity.OTHER,
    diary.ACT1_001.DISPOSAL_OF_WASTE: Activity.OTHER,
    diary.ACT1_001.OTHER_SPECIFIED_HOUSEHOLD_UPKEEP: Activity.OTHER,
    diary.ACT1_001.UNSPECIFIED_MAKING_AND_CARE_FOR_TEXTILES: Activity.OTHER,
    diary.ACT1_001.LAUNDRY: Activity.OTHER,
    diary.ACT1_001.IRONING: Activity.OTHER,
    diary.ACT1_001.HANDICRAFT_AND_PRODUCING_TEXTILES: Activity.OTHER,
    diary.ACT1_001.OTHER_SPECIFIED_MAKING_AND_CARE_FOR_TEXTILES: Activity.OTHER,
    diary.ACT1_001.UNSPECIFIED_GARDENING_AND_PET_CARE: Activity.OTHER,
    diary.ACT1_001.GARDENING: Activity.OTHER,
    diary.ACT1_001.TENDING_DOMESTIC_ANIMALS: Activity.OTHER,
    diary.ACT1_001.CARING_FOR_PETS: Activity.OTHER,
    diary.ACT1_001.WALKING_THE_DOG: Activity.OTHER,
    diary.ACT1_001.OTHER_SPECIFIED_GARDENING_AND_PET_CARE: Activity.OTHER,
    diary.ACT1_001.UNSPECIFIED_CONSTRUCTION_AND_REPAIRS: Activity.OTHER,
    diary.ACT1_001.HOUSE_CONSTRUCTION_AND_RENOVATION: Activity.OTHER,
    diary.ACT1_001.REPAIRS_OF_DWELLING: Activity.OTHER,
    diary.ACT1_001.UNSPECIFIED_MAKING__REPAIRING_AND_MAINTAINING_EQUIPMENT: Activity.OTHER,
    diary.ACT1_001.WOODCRAFT__METAL_CRAFT__SCULPTURE_AND_POTTERY: Activity.OTHER,
    diary.ACT1_001.OTHER_SPECIFIED_MAKING__REPAIRING_AND_MAINTAINING_EQUIPMENT: Activity.OTHER,
    diary.ACT1_001.VEHICLE_MAINTENANCE: Activity.OTHER,
    diary.ACT1_001.OTHER_SPECIFIED_CONSTRUCTION_AND_REPAIRS: Activity.OTHER,
    diary.ACT1_001.UNSPECIFIED_SHOPPING_AND_SERVICES: Activity.OTHER,
    diary.ACT1_001.UNSPECIFIED_SHOPPING: Activity.OTHER,
    diary.ACT1_001.SHOPPING_MAINLY_FOR_FOOD: Activity.OTHER,
    diary.ACT1_001.SHOPPING_MAINLY_FOR_CLOTHING: Activity.OTHER,
    diary.ACT1_001.SHOPPING_MAINLY_RELATED_TO_ACCOMMODATION: Activity.OTHER,
    diary.ACT1_001.SHOPPING_OR_BROWSING_AT_CAR_BOOT_SALES_OR_ANTIQUE_FAIRS: Activity.OTHER,
    diary.ACT1_001.WINDOW_SHOPPING_OR_OTHER_SHOPPING_AS_LEISURE: Activity.OTHER,
    diary.ACT1_001.OTHER_SPECIFIED_SHOPPING: Activity.OTHER,
    diary.ACT1_001.COMMERCIAL_AND_ADMINISTRATIVE_SERVICES: Activity.OTHER,
    diary.ACT1_001.PERSONAL_SERVICES: Activity.OTHER,
    diary.ACT1_001.OTHER_SPECIFIED_SHOPPING_AND_SERVICES: Activity.OTHER,
    diary.ACT1_001.HOUSEHOLD_MANAGEMENT_NOT_USING_THE_INTERNET: Activity.OTHER,
    diary.ACT1_001.UNSPECIFIED_HOUSEHOLD_MANAGEMENT_USING_THE_INTERNET: Activity.OTHER,
    diary.ACT1_001.SHPING_FORANDORDRING_UNSPEC_GDSANDSRVS_VIA_INTERNET: Activity.OTHER,
    diary.ACT1_001.SHPING_FORANDORDRING_FOOD_VIA_THE_INTERNET: Activity.OTHER,
    diary.ACT1_001.SHPING_FORANDORDRING_CLOTHING_VIA_THE_INTERNET: Activity.OTHER,
    diary.ACT1_001.SHPING_FORANDORDRING_GDSANDSRV_RELATED_TO_ACC_VIA_INTERNET: Activity.OTHER,
    diary.ACT1_001.SHPING_FORANDORDRING_MASS_MEDIA_VIA_THE_INTERNET: Activity.OTHER,
    diary.ACT1_001.SHPING_FORANDORDRING_ENTERTAINMENT_VIA_THE_INTERNET: Activity.OTHER,
    diary.ACT1_001.BANKING_AND_BILL_PAYING_VIA_THE_INTERNET: Activity.OTHER,
    diary.ACT1_001.OTHER_SPECIFIED_HOUSEHOLD_MANAGEMENT_USING_THE_INTERNET: Activity.OTHER,
    diary.ACT1_001.UNSPECIFIED_CHILDCARE: Activity.OTHER,
    diary.ACT1_001.UNSPECIFIED_PHYSICAL_CARE_AND_SUPERVISION_OF_A_CHILD: Activity.OTHER,
    diary.ACT1_001.FEEDING_THE_CHILD: Activity.OTHER,
    diary.ACT1_001.OTHER_SPECIFIED_PHYSICAL_CARE_AND_SUPERVISION_OF_A_CHILD: Activity.OTHER,
    diary.ACT1_001.TEACHING_THE_CHILD: Activity.OTHER,
    diary.ACT1_001.READING__PLAYING_AND_TALKING_WITH_CHILD: Activity.OTHER,
    diary.ACT1_001.ACCOMPANYING_CHILD: Activity.OTHER,
    diary.ACT1_001.OTHER_SPECIFIED_CHILDCARE: Activity.OTHER,
    diary.ACT1_001.UNSPECIFIED_HELP_TO_AN_ADULT_HOUSEHOLD_MEMBER: Activity.OTHER,
    diary.ACT1_001.PHYSICAL_CARE_AND_SUPERVISION_OF_AN_ADULT_HOUSEHOLD_MEMBER: Activity.OTHER,
    diary.ACT1_001.ACCOMPANYING_AN_ADULT_HOUSEHOLD_MEMBER: Activity.OTHER,
    diary.ACT1_001.OTHER_SPECIFIED_HELP_TO_AN_ADULT_HOUSEHOLD_MEMBER: Activity.OTHER,
    diary.ACT1_001.UNSPECIFIED_VOLUNTEER_WORK_AND_MEETINGS: Activity.OTHER,
    diary.ACT1_001.UNSPECIFIED_ORGANISATIONAL_WORK: Activity.OTHER,
    diary.ACT1_001.WORK_FOR_AN_ORGANISATION: Activity.OTHER,
    diary.ACT1_001.VOLUNTEER_WORK_THROUGH_AN_ORGANISATION: Activity.OTHER,
    diary.ACT1_001.OTHER_SPECIFIED_ORGANISATIONAL_WORK: Activity.OTHER,
    diary.ACT1_001.UNSPECIFIED_INFORMAL_HELP: Activity.OTHER,
    diary.ACT1_001.FOOD_MANAGEMENT_AS_HELP: Activity.OTHER,
    diary.ACT1_001.HOUSEHOLD_UPKEEP_AS_HELP: Activity.OTHER,
    diary.ACT1_001.GARDENING_AND_PET_CARE_AS_HELP: Activity.OTHER,
    diary.ACT1_001.CONSTRUCTION_AND_REPAIRS_AS_HELP: Activity.OTHER,
    diary.ACT1_001.SHOPPING_AND_SERVICES_AS_HELP: Activity.OTHER,
    diary.ACT1_001.HELP_IN_EMPLOYMENT_AND_FARMING: Activity.OTHER,
    diary.ACT1_001.UNSPECIFIED_CHILDCARE_AS_HELP: Activity.OTHER,
    diary.ACT1_001.PHYSICAL_CARE_AND_SUPERVISION_OF_A_CHILD_AS_HELP: Activity.OTHER,
    diary.ACT1_001.TEACHING_THE_CHILD_AS_HELP: Activity.OTHER,
    diary.ACT1_001.READING__PLAYING_AND_TALKING_TO_THE_CHILD_AS_HELP: Activity.OTHER,
    diary.ACT1_001.ACCOMPANYING_THE_CHILD_AS_HELP: Activity.OTHER,
    diary.ACT1_001.OTHER_SPECIFIED_CHILDCARE_AS_HELP: Activity.OTHER,
    diary.ACT1_001.UNSPECIFIED_HELP_TO_AN_ADULT_MEMBER_OF_ANOTHER_HOUSEHOLD: Activity.OTHER,
    diary.ACT1_001.PHYSICAL_CARE_AND_SUPERVISION_OF_AN_ADULT_AS_HELP: Activity.OTHER,
    diary.ACT1_001.ACCOMPANYING_AN_ADULT_AS_HELP: Activity.OTHER,
    diary.ACT1_001.OTHER_SPECIFIED_HELP_TO_AN_ADULT_MEMBER_OF_ANOTHER_HOUSEHOLD: Activity.OTHER,
    diary.ACT1_001.OTHER_SPECIFIED_INFORMAL_HELP: Activity.OTHER,
    diary.ACT1_001.UNSPECIFIED_PARTICIPATORY_ACTIVITIES: Activity.OTHER,
    diary.ACT1_001.MEETINGS: Activity.OTHER,
    diary.ACT1_001.RELIGIOUS_ACTIVITIES: Activity.OTHER,
    diary.ACT1_001.OTHER_SPECIFIED_PARTICIPATORY_ACTIVITIES: Activity.OTHER,
    diary.ACT1_001.UNSPECIFIED_SOCIAL_LIFE_AND_ENTERTAINMENT: Activity.OTHER,
    diary.ACT1_001.UNSPECIFIED_SOCIAL_LIFE: Activity.OTHER,
    diary.ACT1_001.SOCIALISING_WITH_HOUSEHOLD_MEMBERS: Activity.OTHER,
    diary.ACT1_001.VISITING_AND_RECEIVING_VISITORS: Activity.OTHER,
    diary.ACT1_001.FEASTS: Activity.OTHER,
    diary.ACT1_001.TELEPHONE_CONVERSATION: Activity.OTHER,
    diary.ACT1_001.OTHER_SPECIFIED_SOCIAL_LIFE: Activity.OTHER,
    diary.ACT1_001.UNSPECIFIED_ENTERTAINMENT_AND_CULTURE: Activity.OTHER,
    diary.ACT1_001.CINEMA: Activity.OTHER,
    diary.ACT1_001.UNSPECIFIED_THEATRE_OR_CONCERTS: Activity.OTHER,
    diary.ACT1_001.PLAYS__MUSICALS_OR_PANTOMIMES: Activity.OTHER,
    diary.ACT1_001.OPERA__OPERETTA_OR_LIGHT_OPERA: Activity.OTHER,
    diary.ACT1_001.CONCERTS_OR_OTHER_PERFORMANCES_OF_CLASSICAL_MUSIC: Activity.OTHER,
    diary.ACT1_001.LIVE_MUSIC_OTHER_THAN_CLASSICAL_CONCERTS__OPERA_AND_MUSICALS: Activity.OTHER,
    diary.ACT1_001.DANCE_PERFORMANCES: Activity.OTHER,
    diary.ACT1_001.OTHER_SPECIFIED_THEATRE_OR_CONCERTS: Activity.OTHER,
    diary.ACT1_001.ART_EXHIBITIONS_AND_MUSEUMS: Activity.OTHER,
    diary.ACT1_001.UNSPECIFIED_LIBRARY: Activity.OTHER,
    diary.ACT1_001.BRWING_BKS_RCDS_AUDIO_VIDEO_CDS_VDS_FROM_LIBRARY: Activity.OTHER,
    diary.ACT1_001.REFERENCE_TO_BKS_AND_OTHER_LIBRARY_MATERIALS_WITHIN_LIBRARY: Activity.OTHER,
    diary.ACT1_001.USING_INTERNET_IN_THE_LIBRARY: Activity.OTHER,
    diary.ACT1_001.USING_COMPUTERS_IN_THE_LIBRARY_OTHER_THAN_INTERNET_USE: Activity.OTHER,
    diary.ACT1_001.READING_NEWSPAPERS_IN_A_LIBRARY: Activity.OTHER,
    diary.ACT1_001.LISTENING_TO_MUSIC_IN_A_LIBRARY: Activity.OTHER,
    diary.ACT1_001.OTHER_SPECIFIED_LIBRARY_ACTIVITIES: Activity.OTHER,
    diary.ACT1_001.SPORTS_EVENTS: Activity.OTHER,
    diary.ACT1_001.OTHER_SPECIFIED_ENTERTAINMENT_AND_CULTURE: Activity.OTHER,
    diary.ACT1_001.VISITING_A_HISTORICAL_SITE: Activity.OTHER,
    diary.ACT1_001.VISITING_A_WILDLIFE_SITE: Activity.OTHER,
    diary.ACT1_001.VISITING_A_BOTANICAL_SITE: Activity.OTHER,
    diary.ACT1_001.VISITING_A_LEISURE_PARK: Activity.OTHER,
    diary.ACT1_001.VISITING_AN_URBAN_PARK__PLAYGROUND_OR_DESIGNATED_PLAY_AREA: Activity.OTHER,
    diary.ACT1_001.OTHER_SPECIFIED_ENTERTAINMENT_OR_CULTURE: Activity.OTHER,
    diary.ACT1_001.RESTING_TIME_OUT: Activity.OTHER,
    diary.ACT1_001.UNSPECIFIED_SPORTS_AND_OUTDOOR_ACTIVITIES: Activity.OTHER,
    diary.ACT1_001.UNSPECIFIED_PHYSICAL_EXERCISE: Activity.OTHER,
    diary.ACT1_001.WALKING_AND_HIKING: Activity.OTHER,
    diary.ACT1_001.TAKING_A_WALK_OR_HIKE_THAT_LASTS_AT_LEAST_2_MILES_OR_1_HOUR: Activity.OTHER,
    diary.ACT1_001.OTHER_WALK_OR_HIKE: Activity.OTHER,
    diary.ACT1_001.JOGGING_AND_RUNNING: Activity.OTHER,
    diary.ACT1_001.BIKING__SKIING_AND_SKATING: Activity.OTHER,
    diary.ACT1_001.BIKING: Activity.OTHER,
    diary.ACT1_001.SKIING_OR_SKATING: Activity.OTHER,
    diary.ACT1_001.UNSPECIFIED_BALL_GAMES: Activity.OTHER,
    diary.ACT1_001.INDOOR_PAIRS_OR_DOUBLES_GAMES: Activity.OTHER,
    diary.ACT1_001.INDOOR_TEAM_GAMES: Activity.OTHER,
    diary.ACT1_001.OUTDOOR_PAIRS_OR_DOUBLES_GAMES: Activity.OTHER,
    diary.ACT1_001.OUTDOOR_TEAM_GAMES: Activity.OTHER,
    diary.ACT1_001.OTHER_SPECIFIED_BALL_GAMES: Activity.OTHER,
    diary.ACT1_001.GYMNASTICS: Activity.OTHER,
    diary.ACT1_001.FITNESS: Activity.OTHER,
    diary.ACT1_001.UNSPECIFIED_WATER_SPORTS: Activity.OTHER,
    diary.ACT1_001.SWIMMING: Activity.OTHER,
    diary.ACT1_001.OTHER_SPECIFIED_WATER_SPORTS: Activity.OTHER,
    diary.ACT1_001.OTHER_SPECIFIED_PHYSICAL_EXERCISE: Activity.OTHER,
    diary.ACT1_001.UNSPECIFIED_PRODUCTIVE_EXERCISE: Activity.OTHER,
    diary.ACT1_001.HUNTING_AND_FISHING: Activity.OTHER,
    diary.ACT1_001.PICKING_BERRIES__MUSHROOM_AND_HERBS: Activity.OTHER,
    diary.ACT1_001.OTHER_SPECIFIED_PRODUCTIVE_EXERCISE: Activity.OTHER,
    diary.ACT1_001.UNSPECIFIED_SPORTS_RELATED_ACTIVITIES: Activity.OTHER,
    diary.ACT1_001.ACTIVITIES_RELATED_TO_SPORTS: Activity.OTHER,
    diary.ACT1_001.ACTIVITIES_RELATED_TO_PRODUCTIVE_EXERCISE: Activity.OTHER,
    diary.ACT1_001.UNSPECIFIED_HOBBIES_AND_GAMES: Activity.OTHER,
    diary.ACT1_001.UNSPECIFIED_ARTS: Activity.OTHER,
    diary.ACT1_001.UNSPECIFIED_VISUAL_ARTS: Activity.OTHER,
    diary.ACT1_001.PAINTING__DRAWING_OR_OTHER_GRAPHIC_ARTS: Activity.OTHER,
    diary.ACT1_001.MAKING_VIDEOS__TAKING_PHOTOS_OR_RELATED_ACTIVITIES: Activity.OTHER,
    diary.ACT1_001.OTHER_SPECIFIED_VISUAL_ARTS: Activity.OTHER,
    diary.ACT1_001.UNSPECIFIED_PERFORMING_ARTS: Activity.OTHER,
    diary.ACT1_001.SINGING_OR_OTHER_MUSICAL_ACTIVITIES: Activity.OTHER,
    diary.ACT1_001.OTHER_SPECIFIED_PERFORMING_ARTS: Activity.OTHER,
    diary.ACT1_001.LITERARY_ARTS: Activity.OTHER,
    diary.ACT1_001.OTHER_SPECIFIED_ARTS: Activity.OTHER,
    diary.ACT1_001.UNSPECIFIED_HOBBIES: Activity.OTHER,
    diary.ACT1_001.COLLECTING: Activity.OTHER,
    diary.ACT1_001.COMPUTING_PROGRAMMING: Activity.OTHER,
    diary.ACT1_001.UNSPECIFIED_INFORMATION_BY_COMPUTING: Activity.OTHER,
    diary.ACT1_001.INFORMATION_SEARCHING_ON_THE_INTERNET: Activity.OTHER,
    diary.ACT1_001.OTHER_SPECIFIED_INFORMATION_BY_COMPUTING: Activity.OTHER,
    diary.ACT1_001.UNSPECIFIED_COMMUNICATION_BY_COMPUTER: Activity.OTHER,
    diary.ACT1_001.COMMUNICATION_ON_THE_INTERNET: Activity.OTHER,
    diary.ACT1_001.OTHER_SPECIFIED_COMMUNICATION_BY_COMPUTING: Activity.OTHER,
    diary.ACT1_001.UNSPECIFIED_OTHER_COMPUTING: Activity.OTHER,
    diary.ACT1_001.UNSPECIFIED_INTERNET_USE: Activity.OTHER,
    diary.ACT1_001.OTHER_SPECIFIED_COMPUTING: Activity.OTHER,
    diary.ACT1_001.CORRESPONDENCE: Activity.OTHER,
    diary.ACT1_001.OTHER_SPECIFIED_HOBBIES: Activity.OTHER,
    diary.ACT1_001.UNSPECIFIED_GAMES: Activity.OTHER,
    diary.ACT1_001.SOLO_GAMES_AND_PLAY: Activity.OTHER,
    diary.ACT1_001.UNSPECIFIED_GAMES_AND_PLAY_WITH_OTHERS: Activity.OTHER,
    diary.ACT1_001.BILLIARDS__POOL__SNOOKER_OR_PETANQUE: Activity.OTHER,
    diary.ACT1_001.CHESS_AND_BRIDGE: Activity.OTHER,
    diary.ACT1_001.OTHER_SPECIFIED_PARLOUR_GAMES_AND_PLAY: Activity.OTHER,
    diary.ACT1_001.COMPUTER_GAMES: Activity.OTHER,
    diary.ACT1_001.GAMBLING: Activity.OTHER,
    diary.ACT1_001.OTHER_SPECIFIED_GAMES: Activity.OTHER,
    diary.ACT1_001.UNSPECIFIED_MASS_MEDIA: Activity.OTHER,
    diary.ACT1_001.UNSPECIFIED_READING: Activity.OTHER,
    diary.ACT1_001.READING_PERIODICALS: Activity.OTHER,
    diary.ACT1_001.READING_BOOKS: Activity.OTHER,
    diary.ACT1_001.OTHER_SPECIFIED_READING: Activity.OTHER,
    diary.ACT1_001.UNSPECIFIED_TV_WATCHING: Activity.OTHER,
    diary.ACT1_001.WATCHING_A_FILM_ON_TV: Activity.OTHER,
    diary.ACT1_001.WATCHING_SPORT_ON_TV: Activity.OTHER,
    diary.ACT1_001.OTHER_SPECIFIED_TV_WATCHING: Activity.OTHER,
    diary.ACT1_001.UNSPECIFIED_VIDEO_WATCHING: Activity.OTHER,
    diary.ACT1_001.WATCHING_A_FILM_ON_VIDEO: Activity.OTHER,
    diary.ACT1_001.WATCHING_SPORT_ON_VIDEO: Activity.OTHER,
    diary.ACT1_001.OTHER_SPECIFIED_VIDEO_WATCHING: Activity.OTHER,
    diary.ACT1_001.UNSPECIFIED_LISTENING_TO_RADIO_AND_MUSIC: Activity.OTHER,
    diary.ACT1_001.UNSPECIFIED_RADIO_LISTENING: Activity.OTHER,
    diary.ACT1_001.LISTENING_TO_MUSIC_ON_THE_RADIO: Activity.OTHER,
    diary.ACT1_001.LISTENING_TO_SPORT_ON_THE_RADIO: Activity.OTHER,
    diary.ACT1_001.OTHER_SPECIFIED_RADIO_LISTENING: Activity.OTHER,
    diary.ACT1_001.LISTENING_TO_RECORDINGS: Activity.OTHER,
    diary.ACT1_001.TRAVEL_RELATED_TO_UNSPECIFIED_TIME_USE: Activity.OTHER,
    diary.ACT1_001.TRAVEL_RELATED_TO_PERSONAL_BUSINESS: Activity.OTHER,
    diary.ACT1_001.TRAVEL_IN_THE_COURSE_OF_WORK: Activity.OTHER,
    diary.ACT1_001.TRAVEL_TO_WORK_FROM_HOME_AND_BACK_ONLY: Activity.OTHER,
    diary.ACT1_001.TRAVEL_TO_WORK_FROM_A_PLACE_OTHER_THAN_HOME: Activity.OTHER,
    diary.ACT1_001.TRAVEL_RELATED_TO_EDUCATION: Activity.OTHER,
    diary.ACT1_001.TRAVEL_ESCORTING_TO_FROM_EDUCATION: Activity.OTHER,
    diary.ACT1_001.TRAVEL_RELATED_TO_HOUSEHOLD_CARE: Activity.OTHER,
    diary.ACT1_001.TRAVEL_RELATED_TO_SHOPPING: Activity.OTHER,
    diary.ACT1_001.TRAVEL_RELATED_TO_SERVICES: Activity.OTHER,
    diary.ACT1_001.TRAVEL_ESCORTING_A_CHILD_OTHER_THAN_EDUCATION: Activity.OTHER,
    diary.ACT1_001.TRAVEL_ESCORTING_AN_ADULT_OTHER_THAN_EDUCATION: Activity.OTHER,
    diary.ACT1_001.TRAVEL_RELATED_TO_ORGANISATIONAL_WORK: Activity.OTHER,
    diary.ACT1_001.TRAVEL_RELATED_TO_INFORMAL_HELP_TO_OTHER_HOUSEHOLDS: Activity.OTHER,
    diary.ACT1_001.TRAVEL_RELATED_TO_RELIGIOUS_ACTIVITIES: Activity.OTHER,
    diary.ACT1_001.TRAVEL_RLT_TO_PARTICIPATORY_ACTV_EXCEPT_REL_ACTV: Activity.OTHER,
    diary.ACT1_001.TRAVEL_TO_VISIT_FRIENDS_RELATIVES_IN_THEIR_HOMES: Activity.OTHER,
    diary.ACT1_001.TRAVEL_RELATED_TO_OTHER_SOCIAL_ACTIVITIES: Activity.OTHER,
    diary.ACT1_001.TRAVEL_RELATED_TO_ENTERTAINMENT_AND_CULTURE: Activity.OTHER,
    diary.ACT1_001.TRAVEL_RELATED_TO_PHYSICAL_EXERCISE: Activity.OTHER,
    diary.ACT1_001.TRAVEL_RELATED_TO_HUNTING_AND_FISHING: Activity.OTHER,
    diary.ACT1_001.TRAVEL_RELATED_TO_PRODUCTIVE_EXCS_EXPT_HUNTING_AND_FISHING: Activity.OTHER,
    diary.ACT1_001.TRAVEL_RELATED_TO_GAMBLING: Activity.OTHER,
    diary.ACT1_001.TRAVEL_RELATED_TO_HOBBIES_OTHER_THAN_GAMBLING: Activity.OTHER,
    diary.ACT1_001.TRAVEL_TO_HOLIDAY_BASE: Activity.OTHER,
    diary.ACT1_001.TRAVEL_FOR_DAY_TRIP_JUST_WALK: Activity.OTHER,
    diary.ACT1_001.OTHER_SPECIFIED_TRAVEL: Activity.OTHER,
    diary.ACT1_001.PUNCTUATING_ACTIVITY: Activity.OTHER,
    diary.ACT1_001.FILLING_IN_THE_TIME_USE_DIARY: Activity.OTHER,
    diary.ACT1_001.NO_MAIN_ACTIVITY__NO_IDEA_WHAT_IT_MIGHT_BE: np.nan,
    diary.ACT1_001.NO_MAIN_ACTIVITY__SOME_IDEA_WHAT_IT_MIGHT_BE: np.nan,
    diary.ACT1_001.ILLEGIBLE_ACTIVITY: np.nan,
    diary.ACT1_001.UNSPECIFIED_TIME_USE: np.nan,
    diary.ACT1_001.MISSING1: np.nan
}


ECONOMIC_ACTIVITY_MAP = {
    individual.ECONACT2.ECON_ACTIVE___EMPLOYEE___FULL_TIME: EconomicActivity.EMPLOYEE_FULL_TIME,
    individual.ECONACT2.ECON_INACTIVE___LONG_TERM_SICK_DISABLED: EconomicActivity.LONG_TERM_SICK,
    individual.ECONACT2.ECON_INACTIVE___OTHER_REASONS_EG_TEMP_SICK__BELIEVES_NO_JOBS:
        EconomicActivity.INACTIVE_OTHER,
    individual.ECONACT2.ECON_INACTIVE___DK_REASONS: EconomicActivity.INACTIVE_OTHER,
    individual.ECONACT2.ADULT___NOT_CLASSIFIABLE_EITHER_EMP__UNEMP_OR_INACTIVE: np.nan,
    individual.ECONACT2.UNDER_16YRS___INELIGIBLE_FOR_EMPLOYMENT_QUESTIONS:
        EconomicActivity.BELOW_16,
    individual.ECONACT2.ECON_ACTIVE___EMPLOYEE___PART_TIME: EconomicActivity.EMPLOYEE_PART_TIME,
    individual.ECONACT2.ECON_ACTIVE___SELF_EMPLOYED___FULL_TIME: EconomicActivity.SELF_EMPLOYED,
    individual.ECONACT2.ECON_ACTIVE___SELF_EMPLOYED___PART_TIME: EconomicActivity.SELF_EMPLOYED,
    individual.ECONACT2.ECON_ACTIVE___DK_EMPSELFFULLPART: np.nan,
    individual.ECONACT2.ECON_ACTIVE___UNEMPLOYED_ILO_DEFINITION: EconomicActivity.UNEMPLOYED,
    individual.ECONACT2.ECON_INACTIVE___RETIRED: EconomicActivity.RETIRED,
    individual.ECONACT2.ECON_INACTIVE___FULL_TIME_STUDENT:
        EconomicActivity.INACTIVE_FULL_TIME_STUDENT,
    individual.ECONACT2.ECON_INACTIVE___LOOKING_AFTER_FAMILY_HOME:
        EconomicActivity.LOOKING_AFTER_HOME
}


QUALIFICATION_MAP = {
    individual.HIQUAL4.DEGREE_LEVEL_QUALIFICATION_OR_ABOVE: Qualification.LEVEL_45,
    individual.HIQUAL4.QUALIFICATIONS___CITY_AND_GUILDS___DK_LEVEL: np.nan,
    individual.HIQUAL4.QUALIFICATIONS___OTHER___BUT_DK_GRADELEVEL: np.nan,
    individual.HIQUAL4.NO_QUALIFICATIONS: Qualification.NO_QUALIFICATIONS,
    individual.HIQUAL4.ELIGIBLE___NO_ANSWER: np.nan,
    individual.HIQUAL4.UNDER_16YRS___INELIGIBLE_FOR_QUALIFICATIONS_QUESTIONS:
        Qualification.BELOW_16,
    individual.HIQUAL4.HIGHER_EDN_BELOW_DEGREE_LEVEL_EG_HNC__NURSING_QUAL: Qualification.LEVEL_3,
    individual.HIQUAL4.A_LEVELS__VOCATIONAL_LEVEL_3_AND_EQUIVLNT_EG_AS_LEVEL__NVQ_3:
        Qualification.LEVEL_3,
    individual.HIQUAL4.O_LEVELS__GCSE_GRADE_A_C__VOCATIONAL_LEVEL_2_AND_EQUIVLNT:
        Qualification.LEVEL_2,
    individual.HIQUAL4.GCSE_BELOW_GRADE_C__CSE__VOCATIONAL_LEVEL_1_AND_EQUIVLNT:
        Qualification.LEVEL_1,
    individual.HIQUAL4.QUALIFICATION_BELOW_GCSEO_LEVEL_EG_TRADE_APPRENTICESHIPS:
        Qualification.APPRENTICESHIP,
    individual.HIQUAL4.OTHER_QUALIFICATION_INCL_PROFESSIONAL__VOCATIONAL__FOREIGN:
        Qualification.OTHER_QUALIFICATION,
    individual.HIQUAL4.QUALIFICATIONS___BUT_DK_WHICH: np.nan,
    individual.HIQUAL4.QUALIFICATIONS___GCSE___BUT_DK_GRADE: np.nan
}


HOUSEHOLDTYPE_MAP = {
    individual.HHTYPE4.SINGLE_PERSON_HOUSEHOLD:
        HouseholdType.ONE_PERSON_HOUSEHOLD,
    individual.HHTYPE4.SINGLE_PARENT___WITH_CHILDREN_GREATEREQUAL_16:
        HouseholdType.LONE_PARENT_WITH_DEPENDENT_CHILDREN,
    individual.HHTYPE4.TWO_OR_MORE_COUPLES_MARRIED_OR_COHAB_WITHWITHOUT_CHILDRN:
        HouseholdType.MULTI_PERSON_HOUSEHOLD,
    individual.HHTYPE4.SAME_SEX_COUPLES___SPONTANEOUSLY_DESCRIBED:
        HouseholdType.COUPLE_WITHOUT_DEPENDENT_CHILDREN,
    individual.HHTYPE4.UNCLASSIFIED___MARRIED_COUPLES_IN_COMPLEX_HHLDS:
        HouseholdType.MULTI_PERSON_HOUSEHOLD,
    individual.HHTYPE4.UNCLASSIFIED___COHABITING_COUPLES_IN_COMPLEX_HHLDS:
        HouseholdType.MULTI_PERSON_HOUSEHOLD,
    individual.HHTYPE4.UNCLASSIFIED___SINGLE_PARENTS_IN_COMPLEX_HHLDS:
        HouseholdType.MULTI_PERSON_HOUSEHOLD,
    individual.HHTYPE4.UNCLASSIFIED___OTHER_HHLDS_WITHOUT_COUPLES_EG_BROTHERS_DK:
        HouseholdType.MULTI_PERSON_HOUSEHOLD,
    individual.HHTYPE4.HHLDS_WITH_2_OR_MORE_UNRELATED_PEOPLE_ONLY:
        HouseholdType.MULTI_PERSON_HOUSEHOLD,
    individual.HHTYPE4.MARRIED_COUPLE___NO_CHILDREN_COUPLE_ONLY:
        HouseholdType.COUPLE_WITHOUT_DEPENDENT_CHILDREN,
    individual.HHTYPE4.MARRIED_COUPLE___WITH_CHILDREN_SMALLEREQUAL_15:
        HouseholdType.COUPLE_WITH_DEPENDENT_CHILDREN,
    individual.HHTYPE4.MARRIED_COUPLE___WITH_CHILDREN_GREATEREQUAL_16:
        HouseholdType.COUPLE_WITH_DEPENDENT_CHILDREN,
    individual.HHTYPE4.COHAB_COUPLE___NO_CHILDREN_COUPLE_ONLY:
        HouseholdType.COUPLE_WITHOUT_DEPENDENT_CHILDREN,
    individual.HHTYPE4.COHAB_COUPLE___WITH_CHILDREN_SMALLEREQUAL_15:
        HouseholdType.COUPLE_WITH_DEPENDENT_CHILDREN,
    individual.HHTYPE4.COHAB_COUPLE___WITH_CHILDREN_GREATEREQUAL_16:
        HouseholdType.COUPLE_WITH_DEPENDENT_CHILDREN,
    individual.HHTYPE4.SINGLE_PARENT____WITH_CHILDREN_SMALLEREQUAL_15:
        HouseholdType.LONE_PARENT_WITH_DEPENDENT_CHILDREN
}


AGE_MAP = {
    8: AgeStructure.AGE_8_TO_9,
    9: AgeStructure.AGE_8_TO_9,
    10: AgeStructure.AGE_10_TO_14,
    11: AgeStructure.AGE_10_TO_14,
    12: AgeStructure.AGE_10_TO_14,
    13: AgeStructure.AGE_10_TO_14,
    14: AgeStructure.AGE_10_TO_14,
    15: AgeStructure.AGE_15,
    16: AgeStructure.AGE_16_TO_17,
    17: AgeStructure.AGE_16_TO_17,
    18: AgeStructure.AGE_18_TO_19,
    19: AgeStructure.AGE_18_TO_19,
    20: AgeStructure.AGE_20_TO_24,
    21: AgeStructure.AGE_20_TO_24,
    22: AgeStructure.AGE_20_TO_24,
    23: AgeStructure.AGE_20_TO_24,
    24: AgeStructure.AGE_20_TO_24,
    25: AgeStructure.AGE_25_TO_29,
    26: AgeStructure.AGE_25_TO_29,
    27: AgeStructure.AGE_25_TO_29,
    28: AgeStructure.AGE_25_TO_29,
    29: AgeStructure.AGE_25_TO_29,
    30: AgeStructure.AGE_30_TO_44,
    31: AgeStructure.AGE_30_TO_44,
    32: AgeStructure.AGE_30_TO_44,
    33: AgeStructure.AGE_30_TO_44,
    34: AgeStructure.AGE_30_TO_44,
    35: AgeStructure.AGE_30_TO_44,
    36: AgeStructure.AGE_30_TO_44,
    37: AgeStructure.AGE_30_TO_44,
    38: AgeStructure.AGE_30_TO_44,
    39: AgeStructure.AGE_30_TO_44,
    40: AgeStructure.AGE_30_TO_44,
    41: AgeStructure.AGE_30_TO_44,
    42: AgeStructure.AGE_30_TO_44,
    43: AgeStructure.AGE_30_TO_44,
    44: AgeStructure.AGE_30_TO_44,
    45: AgeStructure.AGE_45_TO_59,
    46: AgeStructure.AGE_45_TO_59,
    47: AgeStructure.AGE_45_TO_59,
    48: AgeStructure.AGE_45_TO_59,
    49: AgeStructure.AGE_45_TO_59,
    50: AgeStructure.AGE_45_TO_59,
    51: AgeStructure.AGE_45_TO_59,
    52: AgeStructure.AGE_45_TO_59,
    53: AgeStructure.AGE_45_TO_59,
    54: AgeStructure.AGE_45_TO_59,
    55: AgeStructure.AGE_45_TO_59,
    56: AgeStructure.AGE_45_TO_59,
    57: AgeStructure.AGE_45_TO_59,
    58: AgeStructure.AGE_45_TO_59,
    59: AgeStructure.AGE_45_TO_59,
    60: AgeStructure.AGE_60_TO_64,
    61: AgeStructure.AGE_60_TO_64,
    62: AgeStructure.AGE_60_TO_64,
    63: AgeStructure.AGE_60_TO_64,
    64: AgeStructure.AGE_60_TO_64,
    65: AgeStructure.AGE_65_TO_74,
    66: AgeStructure.AGE_65_TO_74,
    67: AgeStructure.AGE_65_TO_74,
    68: AgeStructure.AGE_65_TO_74,
    69: AgeStructure.AGE_65_TO_74,
    70: AgeStructure.AGE_65_TO_74,
    71: AgeStructure.AGE_65_TO_74,
    72: AgeStructure.AGE_65_TO_74,
    73: AgeStructure.AGE_65_TO_74,
    74: AgeStructure.AGE_65_TO_74,
    75: AgeStructure.AGE_75_TO_84,
    76: AgeStructure.AGE_75_TO_84,
    77: AgeStructure.AGE_75_TO_84,
    78: AgeStructure.AGE_75_TO_84,
    79: AgeStructure.AGE_75_TO_84,
    80: AgeStructure.AGE_75_TO_84,
    81: AgeStructure.AGE_75_TO_84,
    82: AgeStructure.AGE_75_TO_84,
    83: AgeStructure.AGE_75_TO_84,
    84: AgeStructure.AGE_75_TO_84,
    85: AgeStructure.AGE_85_TO_89,
    86: AgeStructure.AGE_85_TO_89,
    87: AgeStructure.AGE_85_TO_89,
    88: AgeStructure.AGE_85_TO_89,
    89: AgeStructure.AGE_85_TO_89,
    90: AgeStructure.AGE_90_AND_OVER,
    91: AgeStructure.AGE_90_AND_OVER,
    92: AgeStructure.AGE_90_AND_OVER,
    93: AgeStructure.AGE_90_AND_OVER,
    94: AgeStructure.AGE_90_AND_OVER,
    95: AgeStructure.AGE_90_AND_OVER,
    96: AgeStructure.AGE_90_AND_OVER,
    97: AgeStructure.AGE_90_AND_OVER,
    98: AgeStructure.AGE_90_AND_OVER,
    99: AgeStructure.AGE_90_AND_OVER
}


PSEUDO_MAP = { # mapping from child is arbitrary, could be any other feature
    individual.CHILD.YES: Pseudo.SINGLETON,
    individual.CHILD.NO: Pseudo.SINGLETON,
    np.nan: Pseudo.SINGLETON
}


CARER_MAP = {
    individual.PROVCARE.YES: Carer.CARER,
    individual.PROVCARE.NO: Carer.NO_CARER,
    individual.PROVCARE.DKREFUSE: np.nan
}


PERSONAL_INCOME_MAP = {
    individual.TOTPINC.INELIGIBLE___UNDER_16YRS: PersonalIncome.BELOW_16,
    individual.TOTPINC.INELIGIBLE___NOT_CURRENTLY_EMPLOYED_SELF_EMPLOYED: np.nan,
    individual.TOTPINC._TOTPINC_____________LESS_THAN_GBP__215: PersonalIncome.LESS_THAN_GBP_215,
    individual.TOTPINC.GBP4580_TO_LESS_THAN_GBP6670: PersonalIncome.BETWEEN_GBP_4590_AND_6670,
    individual.TOTPINC.GBP6670_OR_MORE: PersonalIncome.ABOVE_GBP_6670,
    individual.TOTPINC.ELIGIBLE_CURRENT_EMPLOYEE_OR_SELF_EMP___DK_REFUSE_INCOME: np.nan,
    individual.TOTPINC.GBP__215_TO_LESS_THAN_GBP__435: PersonalIncome.BETWEEN_GBP_215_AND_435,
    individual.TOTPINC.GBP__435_TO_LESS_THAN_GBP__870: PersonalIncome.BETWEEN_GBP_435_AND_870,
    individual.TOTPINC.GBP__870_TO_LESS_THAN_GBP1305: PersonalIncome.BETWEEN_GBP_870_AND_1305,
    individual.TOTPINC.GBP1305_TO_LESS_THAN_GBP1740: PersonalIncome.BETWEEN_GBP_1305_AND_1740,
    individual.TOTPINC.GBP1740_TO_LESS_THAN_GBP2820: PersonalIncome.BETWEEN_GBP_1740_AND_2820,
    individual.TOTPINC.GBP2820_TO_LESS_THAN_GBP3420: PersonalIncome.BETWEEN_GBP_2820_AND_3420,
    individual.TOTPINC.GBP3420_TO_LESS_THAN_GBP3830: PersonalIncome.BETWEEN_GBP_3420_AND_3830,
    individual.TOTPINC.GBP3830_TO_LESS_THAN_GBP4580: PersonalIncome.BETWEEN_GBP_3830_AND_4580
}


POPULATION_DENSITY_MAP = {
    individual.POP_DEN2.MISSING: np.nan,
    individual.POP_DEN2._POP_DEN2____0______249: PopulationDensity.UP_TO_249,
    individual.POP_DEN2._250______999: PopulationDensity.BETWEEN_250_AND_999,
    individual.POP_DEN2.N1000___1999: PopulationDensity.BETWEEN_1000_AND_1999,
    individual.POP_DEN2.N2000___2999: PopulationDensity.BETWEEN_2000_AND_2999,
    individual.POP_DEN2.N3000___3999: PopulationDensity.BETWEEN_3000_AND_3999,
    individual.POP_DEN2.N4000___4999: PopulationDensity.BETWEEN_4000_AND_4999,
    individual.POP_DEN2.N5000_OR_MORE_MAX_WAS_JUST_OVER_10_000: PopulationDensity.MORE_THAN_5000
}


REGION_MAP = {
    individual.GORPAF.NORTH_EAST: Region.NORTH_EAST,
    individual.GORPAF.WALES: Region.WALES,
    individual.GORPAF.SCOTLAND: Region.SCOTLAND,
    individual.GORPAF.NORTHERN_IRELAND: Region.NORTHERN_IRELAND,
    individual.GORPAF.NORTH_WEST_INCL_MERSEYSIDE: Region.NORTH_WEST_INCL_MERSEYSIDE,
    individual.GORPAF.YORKSHIRE_AND_HUMBERSIDE: Region.YORKSHIRE_AND_HUMBERSIDE,
    individual.GORPAF.EAST_MIDLANDS: Region.EAST_MIDLANDS,
    individual.GORPAF.WEST_MIDLANDS: Region.WEST_MIDLANDS,
    individual.GORPAF.EASTERN: Region.EASTERN,
    individual.GORPAF.LONDON: Region.LONDON,
    individual.GORPAF.SOUTH_EAST_EXCL_LONDON: Region.SOUTH_EAST_EXCL_LONDON,
    individual.GORPAF.SOUTH_WEST: Region.SOUTH_WEST
}


def dwellingtype_map(row):
    hq13a, hq13b, hq13c, hq13d = row
    if hq13a == household.HQ13A.A_HOUSE_OR_BUNGALOW:
        if hq13b == household.HQ13B.DETACHED:
            return DwellingType.DETACHED_WHOLE_HOUSE_OR_BUNGALOW
        elif hq13b ==  household.HQ13B.SEMI_DETACHED:
            return DwellingType.SEMI_DETACHED_WHOLE_HOUSE_OR_BUNGALOW
        elif hq13b == household.HQ13B.OR_TERRACEEND_OF_TERRACE:
            return DwellingType.TERRACED_WHOLE_HOUSE_OR_BUNGALOW
    elif hq13a == household.HQ13A.A_FLAT_OR_MAISONETTE:
        if hq13c == household.HQ13C.A_PURPOSE_BUILT_BLOCK:
            return DwellingType.FLAT_PURPOSE_BUILT_BLOCK
        elif hq13c == household.HQ13C.A_CONVERTED_HOUSESOME_OTHER_KIND_OF_BUILDING:
            return DwellingType.FLAT_CONVERTED_OR_SHARED_HOUSE
    elif hq13a == household.HQ13A.OTHER:
        if hq13d == household.HQ13D.A_CARAVAN__MOBILE_HOME_OR_HOUSEBOAT:
            return DwellingType.CARAVAN
        if hq13d == household.HQ13D.SOME_OTHER_KIND_OF_ACCOMMODATION:
            return DwellingType.OTHER
    elif hq13a == household.HQ13A.MISSING1:
        return np.nan
    elif hq13a == household.HQ13A.A_ROOMROOMS:
        return DwellingType.OTHER
