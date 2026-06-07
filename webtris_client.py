from abc import ABC, abstractmethod
import requests
from requests.exceptions import HTTPError, Timeout, RequestException
from typing import Optional

class DataGetter(ABC):
    """ The Abstract Base Class that is able to define the interchangeable fetching feature
    """

    """ This defines a network of interchangeable getter algorithms. It allows the 
    ClientWebTRIS or context class to depend on an abstraction instead of
    specific implementations"""
    
    @abstractmethod
    def get_Json(self, url: str, args: dict) -> dict:
        """
        should be implemented by subclasses to get data from the API
        this will receive URL and query args then returns parsed JSON dictionary
        """
        pass

class DataFetch(DataGetter):
    """
    reaches out to WebTRIS API using requests library and implements fetchJson method to get data from the API

    This certain class shows the exact algorithm for hit the current WebTRIS API using requests library by
    implementing the Data Getter. It can also be interchanged at the runtime regardless if changing 
    the ClientWebTRIS syntax. 
    """
    
    def get_Json(self, url: str, args: dict) -> dict:
        """Creates a real HTTP GET request and parses thru the response"""
        try:
            #I set a timeout case so program doesn't hang indefinitely if it is unresponsive, and 
            # can catch it to raise a error message
            response = requests.get(url, params=args, timeout=10)
            # should automatically raise an HTTPError for 404/500 status codes
            response.raise_for_status()
            #can convert JSON text into Python dictionary
            parsed_data = response.json()
            return parsed_data
            
        except Timeout:
            # You can raise this so the client class can handle later
            raise Timeout("Your request to WebTRIS API timed out.")
            
        except HTTPError as error:
            raise HTTPError(f"WebTRIS API returned err: {error.response.status_code}")
            
        except RequestException as error:
            raise RequestException(f"network error occurs: {error}")

class MockDataGetter(DataGetter):
    """
    The mock strategy: Returns mock data for offline testing thus completely bypasses the internet.
    This sequence shows how the algorithm that doesn't use the internet and returns the preset mock-data. 
    By using this for the client when testing, we can segregate the math and parsing from the network 
    external extrema. This satisfies the interchangeable testing feature. 
    """
    
    def __init__(self, fake_data: dict) -> None:
        # stores mock dictionary when a vertain object is created
        self.fake_data: dict = fake_data

    def get_Json(self, url: str, args: dict) -> dict:
        """
        Ignores URL + parameters completely. 
        returns the fake data that is input"""
        return self.fake_data

class MockGetterErr(DataGetter):
    """A mock class that brute-forces an error to test the exception 
    handle cases in the client. Also swappable with  
    client regardless of changing the client logic showing the strategy 
    pattern/composition functioning"""
    def get_Json(self, url: str, args: dict) -> dict:
        raise Timeout("Predetermined timeout error during testing")


class TrafficObservation:
    """
    should represent a 15 min traffic observation from a sensor site
     handles data conversion and gives sorting in chronological order abilities
    """

    def __init__(self, site_name: str, reportdate: str, timeperiod: str, avg_mph: str, total_vol: str) -> None:
        self.site_name: str = site_name
        self.reportdate: str = reportdate
        self.timeperiod: str = timeperiod
        # declares type hints for attributes that could be None
        self.avg_mph: Optional[int] 
        self.total_vol: Optional[int]
        
        # Convert string vals to integers + handles the API's empty strings
        if avg_mph == "":
            self.avg_mph = None
        else:
            self.avg_mph = int(avg_mph)

        # Check + convert total vol, which can also be an empty string
        if total_vol == "":
            self.total_vol = None
        else:
            self.total_vol = int(total_vol)

    def isvalid(self) -> bool:
        """
        finds if whether or not the record has a valid, complete data
        Returns True if the speed and volume both are present
        """
        return self.avg_mph is not None and self.total_vol is not None

    def __lt__(self, other: object) -> bool:
        """
        Implements a comparison to sort records in chronological order
        """
        if not isinstance(other, TrafficObservation):
            raise TypeError("Comparisons can only be between TrafficObservation objects only.")
            
        # ISO8601 formated strings (year-month-day YY:MM:DD) and sorted in chronological order rising
        # as  strings they should merge date + time period ending up in correct order if they are compared
        self_timestamp: str = f"{self.reportdate}_{self.timeperiod}"
        other_timestamp: str = f"{other.reportdate}_{other.timeperiod}"
        
        return self_timestamp < other_timestamp

    def __eq__(self, oth: object) -> bool:
        """
        implements equality based upon site + exact time for the observation
        """
        if not isinstance(oth, TrafficObservation):
            return False
            
        return (self.site_name == oth.site_name and 
                self.reportdate == oth.reportdate and 
                self.timeperiod == oth.timeperiod)

    def __hash__(self) -> int:
        """lets the observation be hashed based on its  attributes that define its identity (site + time)"""
        return hash((self.site_name, self.reportdate, self.timeperiod))

    def __repr__(self) -> str:
        """returns string repr of the object for dev/debug purposes"""
        return (f'TrafficObservation(site_name={self.site_name!r}, '
                f'report_date={self.reportdate!r}, time={self.timeperiod!r}, '
                f'speed={self.avg_mph}, volume={self.total_vol})')

    def __str__(self) -> str:
        """should return a string version for the user at the end"""
        status: str = "Valid" if self.isvalid() else "Missing Data"
        return f"[{self.site_name}] {self.reportdate} at {self.timeperiod} | Speed: {self.avg_mph}mph | Vol: {self.total_vol} ({status})"


class Site:
    """
    Represents a single traffic sensor site + manages collection of TrafficObservation objects for a day
    """
    def __init__(self, site_ID: str, site_name: str) -> None:
        self.site_ID: str = site_ID
        self.site_name: str = site_name
        self.observ_list: list[TrafficObservation] = []


    def plus_Observation(self, observation: TrafficObservation) -> None:
        """should add a new observation to the site's collection"""
        self.observ_list.append(observation)


    def __len__(self) -> int:
        """Finds the num of records in the collection"""
        return len(self.observ_list)


    def __iter__(self):
        """Allows for iteration over records chronologicalally"""
        # Sorting them directlyl using  __lt__ which using method built in the TrafficObservation class
        return iter(sorted(self.observ_list))

    def avg_mph(self) -> float:
        """Finds avg speed found across all the records with valid data inputs"""
        validRecs = [obs for obs in self.observ_list if obs.isvalid()]
        if not validRecs:
            return 0.0
        
        total_speed = 0
        for obs in validRecs:
            if obs.avg_mph is not None:
                total_speed += int(obs.avg_mph)
        return total_speed / len(validRecs)



    def total_vol(self) -> int:
        """calculates the total vehicle volume found across all records"""
        validRecs = [obs for obs in self.observ_list if obs.isvalid()]
        
        total_volume = 0
        for obs in validRecs:
            if obs.total_vol is not None:
                total_volume += int(obs.total_vol)
            
        return total_volume


    def get_hr_recs(self, hourStr: str) -> list[TrafficObservation]:
        """
        gets all records for a given hour. Expects hourStr in format 'HH' or '08' or '14'.
        """
        # The api returns timeperiod as "HH:MM:ss" - so can check if it starts with requested hour or not
        prefix = f"{hourStr}:"
        return [obs for obs in self.observ_list if obs.timeperiod.startswith(prefix)]


    def avg_mph_hr(self, hourStr: str) -> float:
        """finds avg speed for the given hour"""
        hourRecs = self.get_hr_recs(hourStr)
        validRecs = [obs for obs in hourRecs if obs.isvalid()]
        
        if not validRecs:
            return 0.0     
        total_speed = 0
        for obs in validRecs:
            if obs.avg_mph is not None:
                total_speed += int(obs.avg_mph)
            
        return total_speed /len(validRecs)
    


    def total_vol_hr(self, hourStr: str) -> int:
        """Finds total vol for a certain given hour"""
        hour_recs = self.get_hr_recs(hourStr)
        valid_recs = [obs for obs in hour_recs if obs.isvalid()]
        
        total_volume = 0
        for obs in valid_recs:
            if obs.total_vol is not None:
                total_volume += int(obs.total_vol)
            
        return total_volume


    def find_peak_hr(self) -> str:
        """
        Finds hour with highest traffic volume and Returns the hour string (such as '17' for 5 PM)
        """
        peak_hr = "00"
        max_vol = -1
        
        #should loop from 0 through 23
        for i in range(24):
            # should format the single digits to have leading zero so 0 will becomes 00, 1 becomes 01, etc
            if i < 10:
                hourStr = f"0{i}"
            else:
                hourStr = str(i)
                
            # calculates the volume for given specific hr and compare to max vol, if above: updates the peak hr/max vol
            vol = self.total_vol_hr(hourStr)
            
            if vol > max_vol:
                max_vol = vol
                peak_hr = hourStr
                
        return peak_hr
    def fetch_api_info(self, client, reqDate: str) -> None:
        """
        completes the req to get data by using the class by using the called 
        ClientWebTRIS to get the json for parsing. It can then transmit the 
        data populated to the site collection. 

        fetch data using a given class.
        uses the API client, gets data, then updates the site's internal list
        """
        #call to the client to return a fully populated Site object
        fetched_site = client.report_getter(self.site_ID, reqDate)
        
        #Update the current site with fetched data
        self.site_name = fetched_site.site_name
        self.observ_list = fetched_site.observ_list

class ClientWebTRIS:
    """
    Class manages communication with the WebTRIS API 
    Uses composition to accept any getter strategy that is live or mock
    This context class will maintain the communication with WebTRIS API 
    and gives the real data fetching process to the DataGetter algorithm. 
    This is a strategy pattern/abstract classes, and by utilizing composition 
    (has-a relationship) through our constructor, it allows for the interchanging 
    between fake and real data without the need for changing the client logic. 
    """

    def __init__(self, getter: DataGetter) -> None:
        self.getter: DataGetter = getter
        self.base_url: str = "https://webtris.nationalhighways.co.uk/api/v1.0"

    def report_getter(self, site_ID: str, reqDate: str) -> Site:
        """ Constructs  URL and arguments, and gets the JSON, then parses it into a Site object that is populated
        reqDate is formatted as DDMMYYYY which follows the the API
        """
        url = f"{self.base_url}/reports/daily"
        # start_date / end_date are identical to getter a single day without pagination
        args = {
            "sites": site_ID,
            "start_date": reqDate,
            "end_date": reqDate,
            "page": 1,
            "page_size": 500
        }
        #gets the unaltered dictionary using whatever given strategy was passed as input
        undef_data = self.getter.get_Json(url, args)

        #figures out the site name. If  API returns empty rows, fallback to the ID
        site_name = "UnknownSite"
        rows = undef_data.get("Rows", [])
        if len(rows) > 0:
            site_name = rows[0].get("Site Name", site_ID)

        # Initialize Site container
        targetSite = Site(site_ID, site_name)

        # Parse thru JSON rows into the TrafficObservation objects
        for row in rows:
            obs = TrafficObservation(
                site_name=row.get("Site Name", site_name),
                reportdate=row.get("Report Date", ""),
                timeperiod=row.get("Time Period Ending", ""),
                avg_mph=row.get("Avg mph", ""),
                total_vol=row.get("Total Volume", "")
            )
            targetSite.plus_Observation(obs)
        return targetSite

