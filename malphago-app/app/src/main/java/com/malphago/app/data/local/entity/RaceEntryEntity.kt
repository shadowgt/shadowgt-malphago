package com.malphago.app.data.local.entity

import androidx.room.Entity
import androidx.room.ForeignKey
import androidx.room.Index
import androidx.room.PrimaryKey

@Entity(
    tableName = "race_entry",
    foreignKeys = [
        ForeignKey(
            entity = RaceEntity::class,
            parentColumns = ["id"],
            childColumns = ["raceId"],
            onDelete = ForeignKey.CASCADE,
        ),
    ],
    indices = [Index("raceId")],
)
data class RaceEntryEntity(
    @PrimaryKey val id: Int,
    val raceId: Int,
    val horseNumber: Int?,
    val horseName: String?,
    val jockeyName: String?,
    val trainerName: String?,
    val ranking: Int?,
    val favorRanking: Int?,
    val rating: Int?,
    val weight: String?,
    val horseWeight: Int?,
    val horseWeightChange: Int?,
    val raceInterval: Int?,
    val finishMargin: String?,
    val oddsWin: Double?,
    val oddsPlace: Double?,
    val equipment: String?,
    // 예측 점수 (로컬 캐시)
    val predictionScore: Double?,
    val predictedRank: Int?,
)
