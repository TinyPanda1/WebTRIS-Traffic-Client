import pytest
from requests.exceptions import Timeout
from webtris_client import TrafficObservation, Site, MockDataGetter, ClientWebTRIS, MockGetterErr

@pytest.fixture
def mock_test_api() -> dict:
    """
    gives mock JSON data to our MockDataGetter
    and helps to avoid repetition and prevented making real network requests
    """
    mockDict = {
        "Rows": [
            {
                "Site Name": "Test Site Alpha",
                "Report Date": "2025-10-19T00:00:00",
                "Time Period Ending": "08:14:00",
                "Avg mph": "60",
                "Total Volume": "150"
            },
            {
                "Site Name": "Test Site Alpha",
                "Report Date": "2025-10-19T00:00:00",
                "Time Period Ending": "08:29:00",
                "Avg mph": "",            # Edge case- no speed
                "Total Volume": ""        # Edge case- no vol
            },
            {
                "Site Name": "Test Site Alpha",
                "Report Date": "2025-10-19T00:00:00",
                "Time Period Ending": "09:14:00",
                "Avg mph": "70",
                "Total Volume":  "200"
            }
        ]
    }
    return mockDict

def test_stringtoint() -> None:
    """This tests that a regular observation can propoerly parse the strings to ints"""

    obs = TrafficObservation("SiteBeta", "2025-10-19", "08:00:00", "55", "100")
    
    assert obs.isvalid()
    assert obs.avg_mph == 55
    assert obs.total_vol == 100

def test_empty_str() -> None:
    """Tests that the empty strings from API are found and are treated as the as edge cases"""

    obs = TrafficObservation("SiteBeta", "2025-10-19", "08:15:00", "", "")
    
    # this should flag observation as being an invalid format, since it can't parse the empty strings to ints

    assert not obs.isvalid()
    
    #  should store None instead of crashing on int("")

    assert obs.avg_mph is None
    assert obs.total_vol is None

def test_chronos() -> None:
    """Tests the __lt__ magic method to ensure observations sort by time."""

    obs_early =TrafficObservation("SiteBeta", "2025-10-19", "08:00:00", "50", "100")
    obs_late = TrafficObservation("SiteBeta", "2025-10-19", "09:00:00", "50", "100")
    
    # since it was early, this should pass through as less then late

    assert obs_early < obs_late


def test_invalid_rec() -> None:
    """Tests that the site math methods go past any of the invalid records completely"""

    testSite = Site("123", "Test Site")
    
    # I created these three specific test observations
    obs1 = TrafficObservation("Test Site", "2025-10-19", "08:00:00", "50", "100")
    obs2 = TrafficObservation("Test Site", "2025-10-19", "08:15:00", "", "")  # null edge case
    obs3 = TrafficObservation("Test Site", "2025-10-19", "08:30:00", "70", "200")
    
    # Add them to site
    testSite.plus_Observation(obs1)
    testSite.plus_Observation(obs2)
    testSite.plus_Observation(obs3)
    
    # Check the avg speed - 50+70 / 2 = 60.0
    # The empty rec should be ignored
    assert testSite.avg_mph() == 60.0
    
    # check the total volume - 100+200=300
    assert testSite.total_vol() == 300


def test_interchangeable(mock_test_api: dict) -> None:
    """
    this tests the interchangeable data fetching feature of the client. 
    Should Prove we can input the mock responses using Composition or Strategy Pattern from Week 6 Lecture
    """
    # creates a fake getter and the fixture data
    inter_getter = MockDataGetter(mock_test_api)
    
    # Input mock getter into  client to create a ClientWebTRIS instantiation (Dependency Injection)
    client = ClientWebTRIS(inter_getter)
    
    # call to  client to get initialized Site object
    outcome_site = client.report_getter("123", "19102025")
    
    # asserts client parsed through mock JSON fine and created the site object with the correct name and id
    assert len(outcome_site) == 3
    assert outcome_site.site_name == "Test Site Alpha"
    
    # Confirms calculation continues to function on  parsed site
    assert outcome_site.avg_mph() == 65.0  # (60 + 70)/ 2
    assert outcome_site.total_vol() == 350   # 150 + 200
    assert outcome_site.find_peak_hr() == "09" # Hour 09 had 200 volume, Hour 08 had 150

def test_api_errors() -> None:
    """Tests that client correctly raises the errors during API failures and 
    that the errors are properly raised to the caller (main) without crashing the program."""
    # Call the broken mock strategy
    error_getter = MockGetterErr()
    client = ClientWebTRIS(error_getter)
    
    # Asserts that the call to the client raised an expected error
    with pytest.raises(Timeout):
        client.report_getter("123", "19102025")

