package com.malphago.app.data.local.dao

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import com.malphago.app.data.local.entity.RaceEntity
import com.malphago.app.data.local.entity.RaceEntryEntity
import kotlinx.coroutines.flow.Flow

@Dao
interface RaceDao {

    @Query("SELECT * FROM race WHERE trackCode = :trackCode AND raceDate = :date ORDER BY raceNumber")
    fun getRacesByTrackAndDate(trackCode: String, date: String): Flow<List<RaceEntity>>

    @Query("SELECT * FROM race WHERE id = :raceId")
    suspend fun getRaceById(raceId: Int): RaceEntity?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertRaces(races: List<RaceEntity>)

    @Query("SELECT * FROM race_entry WHERE raceId = :raceId ORDER BY horseNumber")
    fun getEntriesByRace(raceId: Int): Flow<List<RaceEntryEntity>>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertEntries(entries: List<RaceEntryEntity>)

    @Query("DELETE FROM race WHERE raceDate < :beforeDate")
    suspend fun deleteOldRaces(beforeDate: String)
}
