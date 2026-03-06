import React from 'react';
import { render, screen, fireEvent } from ' @testing-library/react-native';
import PrimaryButton from '../PrimaryButton';
import { ActivityIndicator, StyleSheet } from 'react-native';

describe('PrimaryButton', () => {
  it('renders correctly with title prop', () => {
    render(<PrimaryButton title="Test Button" onPress={() => {}} />);
    expect(screen.getByTestId('primary-button')).toBeTruthy();
  });

  it('displays the title text', () => {
    const buttonTitle = 'Click Me';
    render(<PrimaryButton title={buttonTitle} onPress={() => {}} />);
    expect(screen.getByText(buttonTitle)).toBeTruthy();
  });

  it('applies disabled styling when disabled=true', () => {
    render(<PrimaryButton title="Disabled Button" onPress={() => {}} disabled />);
    const button = screen.getByTestId('primary-button');
    // Check if the disabled style is applied.
    // This assumes `disabledButton` style adds a distinct background color.
    expect(button.props.style).toContainEqual(expect.objectContaining({ backgroundColor: '#A0CFFF' }));
  });

  it('prevents onPress when disabled=true', () => {
    const mockOnPress = jest.fn();
    render(<PrimaryButton title="Disabled Button" onPress={mockOnPress} disabled />);
    const button = screen.getByTestId('primary-button');
    fireEvent.press(button);
    expect(mockOnPress).not.toHaveBeenCalled();
  });

  it('shows ActivityIndicator when loading=true', () => {
    render(<PrimaryButton title="Loading Button" onPress={() => {}} loading />);
    expect(screen.getByTestId('activity-indicator')).toBeTruthy();
  });

  it('hides title text when loading=true', () => {
    const buttonTitle = 'Loading Button';
    render(<PrimaryButton title={buttonTitle} onPress={() => {}} loading />);
    expect(screen.queryByText(buttonTitle)).toBeNull();
  });

  it('prevents onPress when loading=true', () => {
    const mockOnPress = jest.fn();
    render(<PrimaryButton title="Loading Button" onPress={mockOnPress} loading />);
    const button = screen.getByTestId('primary-button');
    fireEvent.press(button);
    expect(mockOnPress).not.toHaveBeenCalled();
  });

  it('onPress callback fires when button pressed', () => {
    const mockOnPress = jest.fn();
    render(<PrimaryButton title="Enabled Button" onPress={mockOnPress} />);
    const button = screen.getByTestId('primary-button');
    fireEvent.press(button);
    expect(mockOnPress).toHaveBeenCalledTimes(1);
  });

  it('TouchableOpacity activeOpacity is 0.8', () => {
    render(<PrimaryButton title="Test" onPress={() => {}} />);
    const button = screen.getByTestId('primary-button');
    expect(button.props.activeOpacity).toBe(0.8);
  });

  it('disabled defaults to false', () => {
    const mockOnPress = jest.fn();
    render(<PrimaryButton title="Default Enabled" onPress={mockOnPress} />);
    const button = screen.getByTestId('primary-button');
    fireEvent.press(button);
    expect(mockOnPress).toHaveBeenCalledTimes(1);
  });

  it('loading defaults to false', () => {
    const buttonTitle = 'Default Not Loading';
    render(<PrimaryButton title={buttonTitle} onPress={() => {}} />);
    expect(screen.getByText(buttonTitle)).toBeTruthy();
    expect(screen.queryByTestId('activity-indicator')).toBeNull();
  });

  it('updates when props change from disabled to enabled', () => {
    const mockOnPress = jest.fn();
    const { rerender } = render(<PrimaryButton title="Test" onPress={mockOnPress} disabled />);
    const button = screen.getByTestId('primary-button');
    fireEvent.press(button);
    expect(mockOnPress).not.toHaveBeenCalled();

    rerender(<PrimaryButton title="Test" onPress={mockOnPress} disabled={false} />);
    fireEvent.press(button);
    expect(mockOnPress).toHaveBeenCalledTimes(1);
  });

  it('updates when props change from loading to not loading', () => {
    const mockOnPress = jest.fn();
    const { rerender } = render(<PrimaryButton title="Test" onPress={mockOnPress} loading />);
    expect(screen.queryByText('Test')).toBeNull();
    expect(screen.getByTestId('activity-indicator')).toBeTruthy();

    rerender(<PrimaryButton title="Test" onPress={mockOnPress} loading={false} />);
    expect(screen.getByText('Test')).toBeTruthy();
    expect(screen.queryByTestId('activity-indicator')).toBeNull();
    fireEvent.press(screen.getByText('Test'));
    expect(mockOnPress).toHaveBeenCalledTimes(1);
  });
});
