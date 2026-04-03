package com.malphago.app.data.remote.api

import com.malphago.app.data.remote.dto.RaceDto
import com.malphago.app.data.remote.dto.RaceEntryDto
import retrofit2.http.GET
import retrofit2.http.Path
import retrofit2.http.Query

interface MalPhaGoApi {

    @GET("races")
    suspend fun getRaces(
        @Query("track") track: String? = null,
        @Query("date") date: String? = null,
    ): List<RaceDto>

    @GET("races/{raceId}/entries")
    suspend fun getRaceEntries(@Path("raceId") raceId: Int): List<RaceEntryDto>

    @GET("horses/{horseId}/stats")
    suspend fun getHorseStats(@Path("horseId") horseId: Int): Map<String, Any>

    @GET("jockeys/{jockeyId}/stats")
    suspend fun getJockeyStats(@Path("jockeyId") jockeyId: Int): Map<String, Any>

    @GET("predictions/race/{raceId}")
    suspend fun getRacePredictions(@Path("raceId") raceId: Int): List<Map<String, Any>>
}
