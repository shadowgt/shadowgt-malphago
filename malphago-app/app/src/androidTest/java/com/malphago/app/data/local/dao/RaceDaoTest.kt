package com.malphago.app.data.local.dao

import androidx.room.Room
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.malphago.app.data.local.MalPhaGoDatabase
import com.malphago.app.data.local.entity.RaceEntity
import com.malphago.app.data.local.entity.RaceEntryEntity
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.test.runTest
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class RaceDaoTest {

    private lateinit var database: MalPhaGoDatabase
    private lateinit var dao: RaceDao

    @Before
    fun setup() {
        database = Room.inMemoryDatabaseBuilder(
            ApplicationProvider.getApplicationContext(),
            MalPhaGoDatabase::class.java,
        ).allowMainThreadQueries().build()
        dao = database.raceDao()
    }

    @After
    fun tearDown() {
        database.close()
    }

    private fun sampleRace(id: Int = 1, track: String = "S", date: String = "2025-04-19", number: Int = 3) =
        RaceEntity(
            id = id,
            trackCode = track,
            raceDate = date,
            raceNumber = number,
            raceName = "국3",
            raceLevel = "국3",
            distance = 1400,
            weather = "맑음",
            moisture = "건조",
            totalEntries = 8,
            prize1st = 45000000,
            raceTime = "11:30",
        )

    private fun sampleEntry(id: Int = 1, raceId: Int = 1, horseNumber: Int = 1) =
        RaceEntryEntity(
            id = id,
            raceId = raceId,
            horseNumber = horseNumber,
            horseName = "번개호",
            jockeyName = "김동수",
            trainerName = "이영호",
            ranking = null,
            favorRanking = 2,
            rating = 72,
            weight = "57",
            horseWeight = 452,
            horseWeightChange = 2,
            raceInterval = 21,
            finishMargin = null,
            oddsWin = 3.5,
            oddsPlace = 1.8,
            equipment = null,
            predictionScore = null,
            predictedRank = null,
        )

    @Test
    fun insertAndGetRaces() = runTest {
        val races = listOf(
            sampleRace(id = 1, number = 1),
            sampleRace(id = 2, number = 2),
            sampleRace(id = 3, number = 3),
        )
        dao.insertRaces(races)

        val result = dao.getRacesByTrackAndDate("S", "2025-04-19").first()
        assertEquals(3, result.size)
        assertEquals(1, result[0].raceNumber) // ordered by raceNumber
        assertEquals(2, result[1].raceNumber)
        assertEquals(3, result[2].raceNumber)
    }

    @Test
    fun getRacesByTrackFiltersCorrectly() = runTest {
        dao.insertRaces(
            listOf(
                sampleRace(id = 1, track = "S"),
                sampleRace(id = 2, track = "B"),
            ),
        )

        val seoul = dao.getRacesByTrackAndDate("S", "2025-04-19").first()
        assertEquals(1, seoul.size)
        assertEquals("S", seoul[0].trackCode)

        val busan = dao.getRacesByTrackAndDate("B", "2025-04-19").first()
        assertEquals(1, busan.size)
    }

    @Test
    fun getRaceById() = runTest {
        dao.insertRaces(listOf(sampleRace(id = 42)))

        val race = dao.getRaceById(42)
        assertNotNull(race)
        assertEquals(42, race!!.id)
        assertEquals(1400, race.distance)
    }

    @Test
    fun getRaceByIdReturnsNullWhenNotFound() = runTest {
        val race = dao.getRaceById(999)
        assertNull(race)
    }

    @Test
    fun insertAndGetEntries() = runTest {
        dao.insertRaces(listOf(sampleRace()))

        val entries = listOf(
            sampleEntry(id = 1, horseNumber = 1),
            sampleEntry(id = 2, horseNumber = 2),
            sampleEntry(id = 3, horseNumber = 3),
        )
        dao.insertEntries(entries)

        val result = dao.getEntriesByRace(1).first()
        assertEquals(3, result.size)
        assertEquals(1, result[0].horseNumber) // ordered by horseNumber
    }

    @Test
    fun entriesCascadeDeleteWithRace() = runTest {
        dao.insertRaces(listOf(sampleRace(id = 1, date = "2025-04-19")))
        dao.insertEntries(listOf(sampleEntry(id = 1, raceId = 1)))

        // Delete old races (before 2025-04-20 deletes our race)
        dao.deleteOldRaces("2025-04-20")

        val entries = dao.getEntriesByRace(1).first()
        assertEquals(0, entries.size)
    }

    @Test
    fun upsertRaceOnConflict() = runTest {
        dao.insertRaces(listOf(sampleRace(id = 1).copy(weather = "맑음")))
        dao.insertRaces(listOf(sampleRace(id = 1).copy(weather = "흐림")))

        val race = dao.getRaceById(1)
        assertEquals("흐림", race!!.weather)
    }

    @Test
    fun deleteOldRacesKeepsRecent() = runTest {
        dao.insertRaces(
            listOf(
                sampleRace(id = 1, date = "2025-04-10"),
                sampleRace(id = 2, date = "2025-04-19"),
            ),
        )

        dao.deleteOldRaces("2025-04-15")

        val old = dao.getRacesByTrackAndDate("S", "2025-04-10").first()
        assertEquals(0, old.size)

        val recent = dao.getRacesByTrackAndDate("S", "2025-04-19").first()
        assertEquals(1, recent.size)
    }
}
