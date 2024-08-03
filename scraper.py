import requests
import os
import pandas as pd
import pygsheets

class Scraper():

    def __init__(self) -> None:
        self.checkEnv()
        self.headers, self.cookies = self.setenv()
        self.params = {
            'count': f'{os.getenv("USER_COUNT_PER_SCRAPE")}',
            'max_id': None
        }
        self.followers = None
        self.followings = None
        self.traitors = None

    def setenv(self):
        return ({"user-agent": self.userAgent,
                 "x-ig-app-id": self.xigID},
                {"sessionid": self.sessionID})
        
    def getUserInfoByUsername(self, username):
        try:
            r = requests.get(f'https://i.instagram.com/api/v1/users/web_profile_info/?username={username}', headers=self.headers)
            rjson = r.json()["data"]["user"]
            return {
                "username": username,
                "name": rjson["full_name"],
                "biography": rjson["biography"],
                "postcount": rjson["edge_owner_to_timeline_media"]["count"],
                "followers": rjson["edge_followed_by"]["count"],
                "followings": rjson["edge_follow"]["count"],
                "id": rjson["id"],
                "pp": rjson["profile_pic_url"],
                "pp_hd": rjson["profile_pic_url_hd"],
            }
        except Exception as e:
            print(e)
            return None

    def getFollowersByUsername(self, username:str, followerNumber:int=1000):
        self.params["max_id"] = None
        scraped = 0
        allFollowers = []
        userinfo = self.getUserInfoByUsername(username=username)
        userid = userinfo["id"]
        followercount = userinfo["followers"]

        while scraped < min(followerNumber, followercount):
            try:
                r = requests.get(f'https://www.instagram.com/api/v1/friendships/{userid}/followers/', params=self.params, headers=self.headers, cookies=self.cookies)
                rjson = r.json()
                if "next_max_id" in rjson:
                    self.params["max_id"] = rjson["next_max_id"]
                followerList = rjson["users"]
                scraped += len(followerList)
                allFollowers.extend(followerList)
                print(f"{scraped}/{min(followerNumber, followercount)}")
            except Exception as e:
                raise Exception(f"Error while scraping the followers: {e}")

        self.followers = pd.DataFrame(allFollowers, columns=['id', 'full_name', 'username', 'profile_pic_url'])

    def getFollowingsByUsername(self, username:str, followingsNumber:int=1000):
        self.params["max_id"] = None
        scraped = 0
        allFollowings = []
        userinfo = self.getUserInfoByUsername(username=username)
        userid = userinfo["id"]
        followingscount = userinfo["followings"]

        while scraped < min(followingsNumber, followingscount):
            try:
                r = requests.get(f'https://www.instagram.com/api/v1/friendships/{userid}/following/', params=self.params, headers=self.headers, cookies=self.cookies)
                rjson = r.json()
                if "next_max_id" in rjson:
                    self.params["max_id"] = rjson["next_max_id"]
                followingList = rjson["users"]
                scraped += len(followingList)
                allFollowings.extend(followingList)
                print(f"{scraped}/{min(followingsNumber, followingscount)}")
            except Exception as e:
                raise Exception(f"Error while scraping the followings: {e}")

        self.followings = pd.DataFrame(allFollowings, columns=['id', 'full_name', 'username', 'profile_pic_url'])

    def getFollowingsButNotFollowers(self):
        self.traitors = self.followings[~self.followings['id'].isin(self.followers['id'])]
        return self.traitors

    def showFollowers(self):
        print(self.followers)

    def writeToSheets(self):
        if not os.path.exists(self.serviceFile):
            raise FileNotFoundError("Service File cannot be found! Please update your .env variables.")
        
        try:
            gc = pygsheets.authorize(service_file=self.serviceFile)
            sh = gc.open_by_url(self.sheetURL)
            wks:pygsheets.Worksheet = sh.worksheet_by_title(self.sheetName)
            wks.set_dataframe(self.traitors, f"A1", nan="")
            print("Sheets updated!")
        except Exception as e:
            print(e)

    def checkEnv(self):
        try:
            self.sessionID = os.getenv("SESSION_ID")
            self.xigID = os.getenv("IG_APP_ID")
            self.userAgent = os.getenv("USER_AGENT")
            self.serviceFile = os.getenv("SERVICE_FILE_PATH")
            self.sheetURL = os.getenv("SHEETS_URL")
            self.sheetName = os.getenv("SHEET_NAME")
        except Exception as e:
            raise Exception("Check your .env variables!")

        if self.sessionID == "":
            raise Exception("Session ID is invalid or expired. Please update it.")
        if self.xigID == "":
            raise Exception("x-ig-app-id is invalid or expired. Please update it.")
        if self.userAgent == "":
            raise Exception("User-Agent is invalid. Please update it.")
        if self.serviceFile == "":
            raise Exception("Service File Path is invalid or expired. Please update it.")
        if self.sheetURL == "":
            raise Exception("Google Sheets URL is invalid or mistyped. Make sure to share the sheet with the service account that is connected to the service file in the environment variables.")
        if self.sheetName == "":
            raise Exception("Google Sheets Name is invalid or mistyped. Please update it.")
        
