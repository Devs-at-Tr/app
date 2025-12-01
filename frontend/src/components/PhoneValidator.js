import React, { useState } from 'react';
import axios from 'axios';
import { Input } from './ui/input';
import { Button } from './ui/button';
import { API } from '../App';

const PhoneValidator = () => {
  const [countryCode, setCountryCode] = useState('+91');
  const [phoneNumber, setPhoneNumber] = useState('');
  const [result, setResult] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  const handleValidate = async () => {
    setIsLoading(true);
    setResult(null);
    setError('');
    try {
      const token = localStorage.getItem('token');
      const resp = await axios.post(
        `${API}/validate-phone`,
        { country_code: countryCode, phone_number: phoneNumber },
        { headers: token ? { Authorization: `Bearer ${token}` } : undefined }
      );
      setResult(resp.data);
    } catch (err) {
      const detail =
        err.response?.data?.detail ||
        err.response?.data?.message ||
        err.message ||
        'Validation failed';
      setError(detail);
    } finally {
      setIsLoading(false);
    }
  };

  React.useEffect(() => {
    if (!countryCode && !phoneNumber) {
      setResult(null);
      setError('');
      return;
    }
    const trimmed = phoneNumber.trim();
    if (!trimmed) {
      setResult(null);
      setError('Enter a phone number');
      return;
    }
    const handle = setTimeout(() => {
      handleValidate();
    }, 400);
    return () => clearTimeout(handle);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [countryCode, phoneNumber]);

  return (
    <div className="space-y-3 p-4 rounded-lg border border-[var(--tg-border-soft)] bg-[var(--tg-surface)]">
      <h3 className="text-lg font-semibold text-[var(--tg-text-primary)]">Phone Validator</h3>
      <div className="flex flex-col sm:flex-row gap-2">
        <Input
          value={countryCode}
          onChange={(e) => setCountryCode(e.target.value)}
          className="sm:w-32"
          placeholder="+91"
        />
        <Input
          value={phoneNumber}
          onChange={(e) => setPhoneNumber(e.target.value)}
          placeholder="Phone number"
          className="flex-1"
        />
        <Button onClick={handleValidate} disabled={isLoading}>
          {isLoading ? 'Validating...' : 'Validate'}
        </Button>
      </div>
      {error && <p className="text-sm text-amber-400">{error}</p>}
      {result && (
        <div className="text-sm space-y-1 text-[var(--tg-text-primary)]">
          <p>
            Status:{' '}
            <span className={result.valid ? 'text-emerald-300' : 'text-amber-400'}>
              {result.valid ? 'Valid' : 'Invalid'}
            </span>
          </p>
          <p>Region: {result.region || 'Unknown'}</p>
          <p>E.164: {result.formatted?.e164 || '—'}</p>
          <p>International: {result.formatted?.international || '—'}</p>
          <p>National: {result.formatted?.national || '—'}</p>
        </div>
      )}
    </div>
  );
};

export default PhoneValidator;
