package com.malphago.app.data.local

import androidx.room.Database
import androidx.room.RoomDatabase
import com.malphago.app.data.local.dao.RaceDao
import com.malphago.app.data.local.entity.RaceEntity
import com.malphago.app.data.local.entity.RaceEntryEntity

@Database(
    entities = [RaceEntity::class, RaceEntryEntity::class],
    version = 1,
    exportSchema = false,
)
abstract class MalPhaGoDatabase : RoomDatabase() {
    abstract fun raceDao(): RaceDao
}
