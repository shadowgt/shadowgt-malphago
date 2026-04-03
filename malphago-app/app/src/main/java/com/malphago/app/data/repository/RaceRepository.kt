package com.malphago.app.data.repository

import com.malphago.app.data.local.dao.RaceDao
import com.malphago.app.data.local.entity.RaceEntity
import com.malphago.app.data.local.entity.RaceEntryEntity
import com.malphago.app.data.remote.api.MalPhaGoApi
import com.malphago.app.data.remote.dto.PredictionDto
import com.malphago.app.data.remote.dto.SynergyDto
import kotlinx.coroutines.flow.Flow
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class RaceRepository @Inject constructor(
    private val api: MalPhaGoApi,
    private val raceDao: RaceDao,
) {
    fun getRacesByTrackAndDate(trackCode: String, date: String): Flow<List<RaceEntity>> =
        raceDao.getRacesByTrackAndDate(trackCode, date)

    fun getEntriesByRace(raceId: Int): Flow<List<RaceEntryEntity>> =
        raceDao.getEntriesByRace(raceId)

    suspend fun syncRaces(trackCode: String, date: String) {
        val raceDtos = api.getRaces(track = trackCode, date = date)
        val entities = raceDtos.map { dto ->
            RaceEntity(
                id = dto.id,
                trackCode = trackCode,
                raceDate = dto.raceDate,
                raceNumber = dto.raceNumber,
                raceName = dto.raceName,
                raceLevel = dto.raceLevel,
                distance = dto.distance,
                weather = dto.weather,
                moisture = null,
                totalEntries = dto.totalEntries,
                prize1st = null,
                raceTime = null,
            )
        }
        raceDao.insertRaces(entities)
    }

    suspend fun syncEntries(raceId: Int) {
        val entryDtos = api.getRaceEntries(raceId)
        val entities = entryDtos.map { dto ->
            RaceEntryEntity(
                id = dto.id,
                raceId = dto.raceId,
                horseNumber = dto.horseNumber,
                horseName = null,
                jockeyName = null,
                trainerName = null,
                ranking = dto.ranking,
                favorRanking = dto.favorRanking,
                rating = dto.rating,
                weight = null,
                horseWeight = dto.horseWeight,
                horseWeightChange = null,
                raceInterval = null,
                finishMargin = null,
                oddsWin = null,
                oddsPlace = null,
                equipment = null,
                predictionScore = null,
                predictedRank = null,
            )
        }
        raceDao.insertEntries(entities)
    }

    suspend fun getPredictions(raceId: Int): List<PredictionDto> =
        api.getRacePredictions(raceId)

    suspend fun runPrediction(raceId: Int) =
        api.runPrediction(raceId)

    suspend fun getRaceSynergies(raceId: Int): List<SynergyDto> =
        api.getRaceSynergies(raceId)
}
