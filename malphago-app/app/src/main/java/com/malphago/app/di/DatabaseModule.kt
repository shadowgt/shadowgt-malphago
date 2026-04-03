package com.malphago.app.di

import android.content.Context
import androidx.room.Room
import com.malphago.app.data.local.MalPhaGoDatabase
import com.malphago.app.data.local.dao.RaceDao
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.android.qualifiers.ApplicationContext
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
object DatabaseModule {

    @Provides
    @Singleton
    fun provideDatabase(@ApplicationContext context: Context): MalPhaGoDatabase {
        return Room.databaseBuilder(
            context,
            MalPhaGoDatabase::class.java,
            "malphago.db",
        ).build()
    }

    @Provides
    fun provideRaceDao(database: MalPhaGoDatabase): RaceDao {
        return database.raceDao()
    }
}
