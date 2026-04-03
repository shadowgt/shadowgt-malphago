package com.malphago.app.data.remote.api

import com.malphago.app.data.remote.dto.*
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Path
import retrofit2.http.Query

interface MalPhaGoApi {

    @GET("races")
    suspend fun getRaces(
        @Query("track") track: String? = null,
        @Query("date") date: String? = null,
    ): List<RaceDto>

    @GET("races/{raceId}")
    suspend fun getRace(@Path("raceId") raceId: Int): RaceDto

    @GET("races/{raceId}/entries")
    suspend fun getRaceEntries(@Path("raceId") raceId: Int): List<RaceEntryDto>

    @GET("horses/{horseId}/stats")
    suspend fun getHorseStats(@Path("horseId") horseId: Int): HorseStatsDto

    @GET("jockeys/{jockeyId}/stats")
    suspend fun getJockeyStats(@Path("jockeyId") jockeyId: Int): JockeyStatsDto

    @GET("predictions/race/{raceId}")
    suspend fun getRacePredictions(@Path("raceId") raceId: Int): List<PredictionDto>

    @POST("predictions/race/{raceId}/run")
    suspend fun runPrediction(@Path("raceId") raceId: Int): Map<String, Any>

    @GET("synergy")
    suspend fun getSynergy(
        @Query("jockeyId") jockeyId: Int,
        @Query("trainerId") trainerId: Int,
        @Query("horseId") horseId: Int? = null,
    ): SynergyDto

    @GET("synergy/race/{raceId}")
    suspend fun getRaceSynergies(@Path("raceId") raceId: Int): List<SynergyDto>

    @GET("notifications/changes")
    suspend fun getRecentChanges(
        @Query("track") track: String? = null,
        @Query("date") date: String? = null,
        @Query("limit") limit: Int = 50,
    ): List<EntryChangeDto>

    @GET("analysis/horse/{horseId}/running-style")
    suspend fun getHorseRunningStyle(
        @Path("horseId") horseId: Int,
        @Query("recent_n") recentN: Int = 10,
    ): RunningStyleDto
}
