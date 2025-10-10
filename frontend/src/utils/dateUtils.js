import { format, formatDistanceToNow } from 'date-fns';
import { formatInTimeZone } from 'date-fns-tz';

const TIMEZONE = 'Asia/Kolkata'; // Mumbai timezone

export const formatMessageTime = (timestamp) => {
  if (!timestamp) return '';
  try {
    // Format directly in Indian time
    return formatInTimeZone(new Date(timestamp), TIMEZONE, 'h:mm a');
  } catch (e) {
    console.error('Error formatting time:', e);
    return '';
  }
};

export const formatMessageDate = (timestamp) => {
  if (!timestamp) return '';
  try {
    const date = new Date(timestamp);
    const now = new Date();
    
    // Format dates in Indian timezone
    const messageDate = formatInTimeZone(date, TIMEZONE, 'yyyy-MM-dd');
    const currentDate = formatInTimeZone(now, TIMEZONE, 'yyyy-MM-dd');
    
    // If the message is from today, show time only
    if (messageDate === currentDate) {
      return formatInTimeZone(date, TIMEZONE, 'h:mm a');
    }
    
    // If it's within the last week, show relative time
    if (now.getTime() - date.getTime() < 7 * 24 * 60 * 60 * 1000) {
      return formatDistanceToNow(date, { addSuffix: true });
    }
    
    // Otherwise show full date
    return formatInTimeZone(date, TIMEZONE, 'MMM d, yyyy h:mm a');
  } catch (e) {
    console.error('Error formatting date:', e);
    return '';
  }
};