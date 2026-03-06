
import { renderHook, act } from '@testing-library/react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { useStreakStore, calculateStreak, calculateWeekProgress } from '../streakStore';
import { STORAGE_KEYS } from '../../data/sampleTerms';

// Mock AsyncStorage
jest.mock('@react-native-async-storage/async-storage', () => ({
  getItem: jest.fn(),
  setItem: jest.fn(),
  clear: jest.fn(),
}));

// Mock Date
const mockDate = new Date('2025-01-15T12:00:00.000Z'); // Wednesday
jest.useFakeTimers().setSystemTime(mockDate);

const mockGetItem = AsyncStorage.getItem as jest.Mock;
const mockSetItem = AsyncStorage.setItem as jest.Mock;

describe('Streak Logic', () => {
  describe('calculateStreak() helper', () => {
    it('should return 0 for an empty array', () => {
      expect(calculateStreak([])).toBe(0);
    });

    it('should return 1 for a single date of today', () => {
      const dates = [new Date('2025-01-15')];
      expect(calculateStreak(dates)).toBe(1);
    });

    it('should return correct streak for consecutive dates', () => {
      const dates = [
        new Date('2025-01-15'),
        new Date('2025-01-14'),
        new Date('2025-01-13'),
      ];
      expect(calculateStreak(dates)).toBe(3);
    });

    it('should return 1 if the most recent date is today but previous is not consecutive', () => {
      const dates = [
        new Date('2025-01-15'),
        new Date('2025-01-13'),
        new Date('2025-01-12'),
      ];
      expect(calculateStreak(dates)).toBe(1);
    });

    it('should handle month boundaries correctly', () => {
        const dates = [
          new Date('2025-02-01'),
          new Date('2025-01-31'),
          new Date('2025-01-30'),
        ];
        // Assuming today is 2025-02-01 for this test case
        jest.useFakeTimers().setSystemTime(new Date('2025-02-01'));
        expect(calculateStreak(dates)).toBe(3);
        jest.useFakeTimers().setSystemTime(mockDate); // Reset mock
    });

    it('should handle leap year boundaries correctly', () => {
        const dates = [
            new Date('2024-03-01'),
            new Date('2024-02-29'),
            new Date('2024-02-28'),
        ];
        jest.useFakeTimers().setSystemTime(new Date('2024-03-01'));
        expect(calculateStreak(dates)).toBe(3);
        jest.useFakeTimers().setSystemTime(mockDate);
    });

    it('should ignore future dates', () => {
      const dates = [
        new Date('2025-01-16'), // Future date
        new Date('2025-01-15'),
        new Date('2025-01-14'),
      ];
      expect(calculateStreak(dates)).toBe(2);
    });
  });

  describe('calculateWeekProgress() helper', () => {
    it('should produce an all-false array for empty dates', () => {
        expect(calculateWeekProgress([])).toEqual([false, false, false, false, false, false, false]);
    });

    it('should correctly calculate day-of-week progress for the current week', () => {
      // Today is Wednesday, Jan 15, 2025
      const dates = [
        new Date('2025-01-13'), // Monday
        new Date('2025-01-15'), // Wednesday
      ];
      const expected = [true, false, true, false, false, false, false];
      expect(calculateWeekProgress(dates)).toEqual(expected);
    });

    it('should handle a full week of activity', () => {
        const dates = [
            new Date('2025-01-13'), // Mon
            new Date('2025-01-14'), // Tue
            new Date('2025-01-15'), // Wed
            new Date('2025-01-16'), // Thu
            new Date('2025-01-17'), // Fri
            new Date('2025-01-18'), // Sat
            new Date('2025-01-19'), // Sun
        ];
        expect(calculateWeekProgress(dates)).toEqual([true, true, true, true, true, true, true]);
    });

    it('should only include dates from the current week (starting Monday)', () => {
        const dates = [
            new Date('2025-01-12'), // Previous Sunday
            new Date('2025-01-13'), // Monday
        ];
        expect(calculateWeekProgress(dates)).toEqual([true, false, false, false, false, false, false]);
    });
  });

  describe('useStreakStore methods', () => {
    beforeEach(() => {
      mockGetItem.mockClear();
      mockSetItem.mockClear();
      // Reset store state before each test
      act(() => {
        useStreakStore.setState({
          studyDates: [],
          currentStreak: 0,
          longestStreak: 0,
          weekProgress: [false, false, false, false, false, false, false],
        }, true);
      });
    });

    describe('loadStreak()', () => {
      it('should load streak data from AsyncStorage and update state', async () => {
        const storedData = {
          studyDates: [new Date('2025-01-14').toISOString()],
          longestStreak: 5,
        };
        mockGetItem.mockResolvedValue(JSON.stringify(storedData));
        
        const { result } = renderHook(() => useStreakStore());

        await act(async () => {
          await result.current.loadStreak();
        });

        expect(mockGetitem).toHaveBeenCalledWith(STORAGE_KEYS.STREAK_DATA);
        expect(result.current.studyDates.length).toBe(1);
        expect(result.current.longestStreak).toBe(5);
        expect(result.current.currentStreak).toBe(1); // Recalculated on load
      });

      it('should handle missing data in AsyncStorage gracefully', async () => {
        mockGetItem.mockResolvedValue(null);
        const { result } = renderHook(() => useStreakStore());

        await act(async () => {
          await result.current.loadStreak();
        });

        expect(result.current.studyDates).toEqual([]);
        expect(result.current.currentStreak).toBe(0);
        expect(result.current.longestStreak).toBe(0);
      });

      it('should handle JSON parsing errors gracefully', async () => {
        mockGetItem.mockResolvedValue('invalid json');
        const { result } = renderHook(() => useStreakStore());
        
        console.error = jest.fn(); // Suppress expected console error

        await act(async () => {
          await result.current.loadStreak();
        });

        expect(result.current.studyDates).toEqual([]);
        expect(result.current.longestStreak).toBe(0);
        expect(console.error).toHaveBeenCalled();
      });
    });

    describe('recordStudySession()', () => {
      it('should add a new session, update streaks, and save to AsyncStorage', async () => {
        const { result } = renderHook(() => useStreakStore());

        await act(async () => {
            await result.current.recordStudySession();
        });

        expect(result.current.studyDates.length).toBe(1);
        expect(result.current.currentStreak).toBe(1);
        expect(result.current.longestStreak).toBe(1);
        expect(result.current.weekProgress[2]).toBe(true); // Wednesday
        expect(mockSetItem).toHaveBeenCalledWith(
            STORAGE_KEYS.STREAK_DATA,
            expect.any(String)
        );
      });

      it('should not add a duplicate entry for the same day', async () => {
        const { result } = renderHook(() => useStreakStore());
        
        await act(async () => {
          await result.current.recordStudySession();
        });
        expect(result.current.studyDates.length).toBe(1);

        // Record a second time on the same day
        await act(async () => {
            await result.current.recordStudySession();
        });

        expect(result.current.studyDates.length).toBe(1);
        expect(mockSetItem).toHaveBeenCalledTimes(1);
      });
      
      it('should update longest streak when current streak exceeds it', async () => {
        const initialState = {
            studyDates: [new Date('2025-01-14')], // Yesterday
            longestStreak: 1
        };
        act(() => {
            useStreakStore.setState(initialState, true);
        });

        const { result } = renderHook(() => useStreakStore());
        
        await act(async () => {
            await result.current.recordStudySession();
        });

        expect(result.current.currentStreak).toBe(2);
        expect(result.current.longestStreak).toBe(2);
      });

      it('should maintain only the last 90 dates', async () => {
        const oldDates = Array.from({ length: 90 }, (_, i) => 
            new Date(`2024-10-${15 + i}`)
        );
        act(() => {
            useStreakStore.setState({ studyDates: oldDates }, true);
        });

        const { result } = renderHook(() => useStreakStore());

        await act(async () => {
            await result.current.recordStudySession();
        });

        expect(result.current.studyDates.length).toBe(90);
        expect(result.current.studyDates[0].toISOString()).toBe(mockDate.toISOString());
        expect(result.current.studyDates[89].toISOString()).toBe(new Date('2024-10-16').toISOString());
      });
    });
  });
});
