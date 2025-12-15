-- MySQL dump 10.13  Distrib 8.4.6, for Linux (x86_64)
--
-- Host: localhost    Database: car
-- ------------------------------------------------------
-- Server version	8.4.6

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `authentication`
--

DROP TABLE IF EXISTS `authentication`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `authentication` (
  `username` varchar(15) NOT NULL,
  `cookie` varchar(250) NOT NULL,
  `expirationDate` datetime NOT NULL,
  PRIMARY KEY (`username`,`cookie`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `futureContacts`
--

DROP TABLE IF EXISTS `futureContacts`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `futureContacts` (
  `contactID` int unsigned NOT NULL AUTO_INCREMENT,
  `name` varchar(25) NOT NULL,
  `startDate` datetime NOT NULL,
  `endDate` datetime NOT NULL,
  `orbit` int NOT NULL,
  `path` int NOT NULL,
  `note` varchar(250) NOT NULL,
  `odfID` int unsigned DEFAULT NULL,
  PRIMARY KEY (`contactID`),
  KEY `odfID` (`odfID`),
  CONSTRAINT `futureContacts_ibfk_1` FOREIGN KEY (`odfID`) REFERENCES `odfFiles` (`odfID`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=4262 DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `futureTargets`
--

DROP TABLE IF EXISTS `futureTargets`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `futureTargets` (
  `futureID` int unsigned NOT NULL AUTO_INCREMENT,
  `targetID` int NOT NULL,
  `startDate` datetime NOT NULL,
  `endDate` datetime NOT NULL,
  `orbit` int NOT NULL,
  `path` int NOT NULL,
  `note` varchar(250) NOT NULL,
  `selected` tinyint(1) NOT NULL DEFAULT '0',
  `odfID` int unsigned DEFAULT NULL,
  PRIMARY KEY (`futureID`),
  KEY `odfID` (`odfID`),
  CONSTRAINT `futureTargets_ibfk_2` FOREIGN KEY (`odfID`) REFERENCES `odfFiles` (`odfID`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=65502 DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `gcs`
--

DROP TABLE IF EXISTS `gcs`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `gcs` (
  `gcID` int unsigned NOT NULL AUTO_INCREMENT,
  `tofID` int unsigned NOT NULL,
  `gcDateTime` datetime NOT NULL,
  `orbit` int DEFAULT NULL,
  PRIMARY KEY (`gcID`),
  UNIQUE KEY `tofID` (`tofID`,`gcDateTime`),
  CONSTRAINT `gcs_ibfk_1` FOREIGN KEY (`tofID`) REFERENCES `tofFiles` (`tofID`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=14887 DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `notes`
--

DROP TABLE IF EXISTS `notes`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `notes` (
  `noteID` int unsigned NOT NULL AUTO_INCREMENT,
  `note` text NOT NULL,
  `startDate` date NOT NULL,
  `endDate` date NOT NULL,
  `userID` int unsigned NOT NULL,
  PRIMARY KEY (`noteID`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `odfFiles`
--

DROP TABLE IF EXISTS `odfFiles`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `odfFiles` (
  `odfID` int unsigned NOT NULL AUTO_INCREMENT,
  `odfFile` varchar(250) NOT NULL,
  `date` date NOT NULL,
  `version` varchar(10) NOT NULL,
  `diffFile` varchar(250) DEFAULT NULL,
  `targetFile` varchar(250) NOT NULL,
  PRIMARY KEY (`odfID`),
  UNIQUE KEY `filename` (`odfFile`)
) ENGINE=InnoDB AUTO_INCREMENT=15239 DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `selectedTargets`
--

DROP TABLE IF EXISTS `selectedTargets`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `selectedTargets` (
  `selectionID` int unsigned NOT NULL AUTO_INCREMENT,
  `targetID` int unsigned NOT NULL,
  `orbit` int DEFAULT NULL,
  `orbitURL` varchar(250) DEFAULT NULL,
  `display` tinyint(1) NOT NULL DEFAULT '1',
  `path` int NOT NULL,
  `pathURL` varchar(250) DEFAULT NULL,
  `targetTimeUTC` datetime NOT NULL,
  `targetTimeLocal` datetime NOT NULL,
  `selectDate` date DEFAULT NULL,
  `emailTime` datetime DEFAULT NULL,
  `tcconDataAvailable` tinyint(1) NOT NULL DEFAULT '0',
  `ocoDataAvailable` tinyint(1) NOT NULL DEFAULT '0',
  `tcconDataStatus` varchar(250) DEFAULT NULL,
  `ocoDataStatus` varchar(250) DEFAULT NULL,
  `tcconDataInfo` varchar(250) DEFAULT NULL,
  `ocoDataInfo` varchar(250) DEFAULT NULL,
  `modisImage` varchar(250) DEFAULT NULL,
  `viirsImage` varchar(250) DEFAULT NULL,
  `aeronetData` varchar(250) DEFAULT NULL,
  `selectedBy` varchar(25) DEFAULT NULL,
  `minGlintAngle` float NOT NULL,
  `obsTime` int DEFAULT NULL,
  `obsMode` varchar(25) DEFAULT NULL,
  `carFile` varchar(250) DEFAULT NULL,
  `tofID` int unsigned NOT NULL,
  `gcID` int unsigned NOT NULL,
  `firstOrbit` int DEFAULT NULL,
  `lastOrbit` int DEFAULT NULL,
  PRIMARY KEY (`selectionID`),
  KEY `targetID` (`targetID`),
  KEY `tofID` (`tofID`),
  KEY `gcID` (`gcID`),
  CONSTRAINT `selectedtargets_ibfk_1` FOREIGN KEY (`targetID`) REFERENCES `sites` (`targetID`) ON DELETE CASCADE,
  CONSTRAINT `selectedtargets_ibfk_2` FOREIGN KEY (`tofID`) REFERENCES `tofFiles` (`tofID`) ON DELETE CASCADE,
  CONSTRAINT `selectedtargets_ibfk_3` FOREIGN KEY (`gcID`) REFERENCES `gcs` (`gcID`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=31617 DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `sites`
--

DROP TABLE IF EXISTS `sites`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `sites` (
  `targetID` int unsigned NOT NULL AUTO_INCREMENT,
  `siteID` int DEFAULT NULL,
  `name` varchar(150) NOT NULL DEFAULT '',
  `description` varchar(250) DEFAULT NULL,
  `targetGeo` point DEFAULT NULL,
  `targetAlt` float DEFAULT NULL,
  `contact` varchar(250) DEFAULT NULL,
  `contactLink` text,
  `tcconStatusText` varchar(250) DEFAULT NULL,
  `tcconStatusValue` tinyint(1) DEFAULT NULL,
  `tcconStatusLink` varchar(250) DEFAULT NULL,
  `emailRecipients` text,
  `display` tinyint(1) NOT NULL DEFAULT '1',
  `tcconGeo` point DEFAULT NULL,
  `tcconAlt` float DEFAULT NULL,
  `timezone` varchar(150) DEFAULT NULL,
  `accuWeatherLink` varchar(250) DEFAULT NULL,
  `wuWeatherLink` varchar(250) DEFAULT NULL,
  PRIMARY KEY (`targetID`,`name`),
  UNIQUE KEY `targetID` (`targetID`)
) ENGINE=InnoDB AUTO_INCREMENT=63 DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `tcconInfo`
--

DROP TABLE IF EXISTS `tcconInfo`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `tcconInfo` (
  `targetID` int unsigned NOT NULL,
  `tcconName` varchar(50) DEFAULT NULL,
  `tcconID` varchar(50) DEFAULT NULL,
  PRIMARY KEY (`targetID`),
  CONSTRAINT `tcconInfo_ibfk_1` FOREIGN KEY (`targetID`) REFERENCES `sites` (`targetID`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `tofFiles`
--

DROP TABLE IF EXISTS `tofFiles`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `tofFiles` (
  `tofID` int unsigned NOT NULL AUTO_INCREMENT,
  `filename` varchar(250) NOT NULL,
  `createTime` datetime NOT NULL,
  `createdBy` varchar(25) DEFAULT NULL,
  `weekOneEmailDate` datetime DEFAULT NULL,
  `createdDate` datetime DEFAULT NULL,
  `modifiedDate` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `maxGCdate` datetime DEFAULT NULL,
  `minGCdate` datetime DEFAULT NULL,
  `ignored` tinyint(1) NOT NULL DEFAULT '0',
  PRIMARY KEY (`tofID`),
  UNIQUE KEY `filename` (`filename`)
) ENGINE=InnoDB AUTO_INCREMENT=717 DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `users`
--

DROP TABLE IF EXISTS `users`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `users` (
  `userID` int unsigned NOT NULL AUTO_INCREMENT,
  `username` varchar(25) NOT NULL,
  `fullName` varchar(50) DEFAULT NULL,
  PRIMARY KEY (`userID`),
  UNIQUE KEY `username` (`username`)
) ENGINE=InnoDB AUTO_INCREMENT=11 DEFAULT CHARSET=latin1 COMMENT='List of users';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2025-10-13 11:37:15
