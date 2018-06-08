/*
 Navicat Premium Data Transfer

 Source Server         : 10.4.80.57 13307
 Source Server Type    : MySQL
 Source Server Version : 50722
 Source Host           : 10.4.80.57:13307
 Source Schema         : focus973

 Target Server Type    : MySQL
 Target Server Version : 50722
 File Encoding         : 65001

 Date: 01/06/2018 14:43:12
*/

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ----------------------------
-- Table structure for rank_stock
-- ----------------------------
DROP TABLE IF EXISTS `rank_stock`;
CREATE TABLE `rank_stock`  (
  `code` char(6) CHARACTER SET utf8 COLLATE utf8_general_ci NOT NULL COMMENT '股票代码',
  `appraiserID` int(255) NULL DEFAULT NULL COMMENT '股评师代码',
  `rank` int(255) NULL DEFAULT NULL COMMENT '排名',
  `timestamp` int(11) NULL DEFAULT NULL COMMENT '时间戳'
) ENGINE = InnoDB CHARACTER SET = utf8 COLLATE = utf8_general_ci ROW_FORMAT = Dynamic;

SET FOREIGN_KEY_CHECKS = 1;
